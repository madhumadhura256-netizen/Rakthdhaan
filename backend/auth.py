import datetime
import re
from datetime import date
from functools import wraps

import jwt
from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, request, g, current_app
from flask_bcrypt import Bcrypt

from otp import phone_is_verified
from database import get_db

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

# Role hierarchy
ROLES = {
    'hospital': 6,
    'admin': 5,
    'doctor': 4,
    'paramedical': 3,
    'blood_connect': 2,  # blood bank staff
    'donor': 1,
    'requester': 0,
}

# Roles anyone may pick when signing up. Staff accounts are created with
# create_staff.py (or by an admin). Never put 'admin' here.
PUBLIC_ROLES = {'donor', 'requester'}

BLOOD_GROUPS = {'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'}
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$')

STOCK_UPDATE_ROLES = {'admin', 'doctor', 'paramedical', 'blood_connect', 'hospital'}
DONATION_RECORD_ROLES = {'admin', 'doctor', 'paramedical', 'blood_connect', 'hospital'}
VERIFY_REQUEST_ROLES = {'admin', 'doctor', 'paramedical', 'blood_connect', 'hospital'}
VIEW_BANKS_ROLES = {
    'admin', 'doctor', 'paramedical', 'blood_connect',
    'donor', 'requester', 'hospital',
}


def _token(user_id, role, email):
    payload = {
        'user_id': user_id,
        'role': role,
        'email': email,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    # PyJWT 1.x returns bytes, 2.x returns str
    return token.decode('utf-8') if isinstance(token, bytes) else token


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """Role check. Always place @token_required ABOVE this decorator."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            user_role = g.current_user.get('role')
            if user_role not in allowed_roles:
                return jsonify({
                    'error': f'Insufficient permissions. Required roles: {", ".join(allowed_roles)}'
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def _num(value, cast):
    """Convert to int/float, or None if empty/invalid."""
    if value in (None, ''):
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


@auth_bp.route('/register', methods=['POST'])
def register():
    db = get_db()
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    role = data.get('role')
    phone = (data.get('phone') or '').strip()
    city = (data.get('city') or '').strip()

    # ---------- common checks ----------
    if not email or not password or not role:
        return jsonify({'error': 'email, password, and role are required'}), 400

    if role not in PUBLIC_ROLES:
        return jsonify({'error': f'Invalid role. Valid roles: {", ".join(sorted(PUBLIC_ROLES))}'}), 400

    if not EMAIL_RE.match(email):
        return jsonify({'error': 'Enter a valid email address'}), 400

    if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return jsonify({'error': 'Password must be 8+ characters with a letter and a number'}), 400

    if db.execute('SELECT id FROM users WHERE email = %s', (email,)).fetchone():
        return jsonify({'error': 'Email already registered'}), 409

    # ---------- donor checks ----------
    donor = None
    if role == 'donor':
        age = _num(data.get('age'), int)
        blood_group = data.get('blood_group', 'O+')
        gender = data.get('gender', 'Male')
        aadhaar = data.get('aadhaar') or None
        weight = _num(data.get('weight'), float)

        if age is None or age < 18 or age > 65:
            return jsonify({'error': 'Donors must be between 18 and 65 years old'}), 400
        if blood_group not in BLOOD_GROUPS:
            return jsonify({'error': 'Invalid blood group'}), 400
        if gender not in ('Male', 'Female', 'Other'):
            return jsonify({'error': 'Invalid gender'}), 400
        if not re.fullmatch(r'[6-9]\d{9}', phone):
            return jsonify({'error': 'Enter a valid 10-digit mobile number'}), 400
        if db.execute('SELECT id FROM donors WHERE phone = %s', (phone,)).fetchone():
            return jsonify({'error': 'This phone number is already registered'}), 409
        if aadhaar:
            if not re.fullmatch(r'[2-9]\d{11}', aadhaar):
                return jsonify({'error': 'Aadhaar must be exactly 12 digits'}), 400
            if db.execute('SELECT id FROM donors WHERE aadhaar = %s', (aadhaar,)).fetchone():
                return jsonify({'error': 'This Aadhaar number is already registered'}), 409
        if weight is not None and weight < 45:
            return jsonify({'error': 'Donors must weigh at least 45 kg'}), 400

        # Donation history: the SERVER decides active/inactive, not the browser
        has_donated = bool(data.get('has_donated_before'))
        last_date = data.get('last_donation_date') or None
        months = 4 if gender == 'Female' else 3
        status = 'active'
        next_eligible = None

        if has_donated:
            if not last_date:
                return jsonify({'error': 'Last donation date is required'}), 400
            try:
                last = date.fromisoformat(last_date)
            except ValueError:
                return jsonify({'error': 'Invalid donation date'}), 400
            if last > date.today():
                return jsonify({'error': 'Donation date cannot be in the future'}), 400
            next_eligible = last + relativedelta(months=months)
            if next_eligible > date.today():
                status = 'inactive'
        else:
            last_date = None

        donor = {
            'name': (data.get('name') or '').strip(),
            'blood_group': blood_group,
            'gender': gender,
            'age': age,
            'phone': phone,
            'city': city,
            'latitude': _num(data.get('latitude'), float),
            'longitude': _num(data.get('longitude'), float),
            'last_donation_date': last_date,
            'aadhaar': aadhaar,
            'weight': weight,
            'previous_hb': _num(data.get('previous_hb'), float),
            'diseases': data.get('diseases') or 'None',
            'bad_habits': data.get('bad_habits') or 'None',
            'disorders': data.get('disorders') or 'None',
            'sms_consent': 1 if data.get('sms_consent') else 0,
            'status': status,
            'has_donated_before': 1 if has_donated else 0,
            'next_eligible_date': next_eligible.isoformat() if next_eligible else None,
            'cooldown_months': months,
            'mobile_verified': 1,
        }
        if len(donor['name']) < 2:
            return jsonify({'error': 'Name is required'}), 400

    # ---------- save ----------
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    cursor = db.execute(
        'INSERT INTO users (email, password_hash, role, phone, city) '
        'VALUES (%s, %s, %s, %s, %s) RETURNING id',
        (email, pw_hash, role, phone, city),
    )
    user_id = cursor.fetchone()['id']

    if donor:
        donor['user_id'] = user_id
        columns = ', '.join(donor)
        marks = ', '.join(['%s'] * len(donor))  # one %s per column
        try:
            db.execute(
                f'INSERT INTO donors ({columns}) VALUES ({marks})',
                list(donor.values()),
            )
        except Exception:
            # Don't leave a half-created account behind
            db.execute('DELETE FROM users WHERE id = %s', (user_id,))
            raise

    db.commit()

    token = _token(user_id, role, email)
    return jsonify({
        'message': 'Registered successfully',
        'token': token,
        'user': {'id': user_id, 'email': email, 'role': role},
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    db = get_db()
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'email and password are required'}), 400

    user = db.execute('SELECT * FROM users WHERE lower(email) = %s', (email,)).fetchone()
    if not user or not bcrypt.check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = _token(user['id'], user['role'], user['email'])
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {'id': user['id'], 'email': user['email'], 'role': user['role']},
    })


@auth_bp.route('/roles', methods=['GET'])
def get_roles():
    """Roles available in the registration dropdown"""
    descriptions = {
        'admin': 'System Administrator - Full access',
        'doctor': 'Medical Doctor - Can verify requests, update stock, record donations',
        'paramedical': 'Paramedical Staff - Can update stock, record donations',
        'blood_connect': 'Blood Bank Staff - Can update stock, record donations',
        'donor': 'Blood Donor - Can register, view profile, search donors',
        'requester': 'Blood Requester - Can create blood requests',
    }
    roles = sorted(PUBLIC_ROLES)
    return jsonify({
        'roles': roles,
        'role_descriptions': {r: descriptions[r] for r in roles},
    })