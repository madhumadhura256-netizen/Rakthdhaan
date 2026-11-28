from flask import Blueprint, jsonify, request, g
from database import get_db
from auth import token_required, role_required

donors_bp = Blueprint('donors', __name__)

# Returned by the public list / detail endpoints
PUBLIC_FIELDS = [
    'id', 'user_id', 'name', 'blood_group', 'gender', 'age', 'phone',
    'latitude', 'longitude', 'city', 'last_donation_date', 'status',
    'cooldown_months', 'is_rare_group', 'created_at', 'total_units_donated',
]
# Only returned to the donor themselves (/me and after profile update)
PRIVATE_FIELDS = [
    'aadhaar', 'weight', 'previous_hb', 'diseases', 'bad_habits',
    'disorders', 'sms_consent', 'donation_codes',
]
EDITABLE_FIELDS = [
    'name', 'blood_group', 'gender', 'age', 'phone', 'latitude', 'longitude',
    'city', 'last_donation_date', 'aadhaar', 'weight', 'previous_hb',
    'diseases', 'bad_habits', 'disorders', 'sms_consent',
]


def _mask_phone(phone, can_see_full):
    """Mask phone number if user doesn't have permission to see full number"""
    if can_see_full or not phone:
        return phone
    # Show first 3 and last 2 digits, mask middle
    if len(phone) > 5:
        return phone[:3] + '***' + phone[-2:]
    return '*****'


def _donor_row_to_dict(row, full=False, can_see_phone=False):
    fields = PUBLIC_FIELDS + (PRIVATE_FIELDS if full else [])
    available = row.keys()
    result = {}
    for k in fields:
        if k in available:
            if k == 'phone':
                result[k] = _mask_phone(row[k], can_see_phone)
            elif k == 'donation_codes':
                try:
                    result[k] = json.loads(row[k]) if row[k] else []
                except (json.JSONDecodeError, TypeError):
                    result[k] = []
            else:
                result[k] = row[k]
    return result


import json


@donors_bp.route('', methods=['GET'])
@donors_bp.route('/', methods=['GET'])
def list_donors():
    db = get_db()
    blood_group = request.args.get('blood_group')
    city = request.args.get('city')
    status = request.args.get('status', 'active')

    # Check if requester has permission to see full phone numbers
    can_see_phone = False
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        # We can't easily check role here without token_required,
        # so default to masked for public endpoint
        pass

    query = 'SELECT * FROM donors WHERE status = %s'
    params = [status]
    if blood_group:
        query += ' AND blood_group = %s'
        params.append(blood_group)
    if city:
        query += ' AND city = %s'
        params.append(city)

    rows = db.execute(query, params).fetchall()
    return jsonify([_donor_row_to_dict(r, full=False, can_see_phone=can_see_phone) for r in rows])


@donors_bp.route('/me', methods=['GET'])
@token_required
def donor_me():
    db = get_db()
    user_id = g.current_user['user_id']
    row = db.execute('SELECT * FROM donors WHERE user_id = %s', (user_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Donor profile not found'}), 404
    # Donor can see their own full details
    return jsonify(_donor_row_to_dict(row, full=True, can_see_phone=True))


@donors_bp.route('/<int:donor_id>', methods=['GET'])
def get_donor(donor_id):
    db = get_db()
    row = db.execute('SELECT * FROM donors WHERE id = %s', (donor_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Donor not found'}), 404
    # Public detail - mask phone
    return jsonify(_donor_row_to_dict(row, full=False, can_see_phone=False))


@donors_bp.route('/<int:donor_id>/full', methods=['GET'])
@token_required
@role_required('admin', 'hospital', 'blood_connect', 'doctor', 'paramedical')
def get_donor_full(donor_id):
    """Full donor details including phone - only for authorized roles"""
    db = get_db()
    row = db.execute('SELECT * FROM donors WHERE id = %s', (donor_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Donor not found'}), 404
    return jsonify(_donor_row_to_dict(row, full=True, can_see_phone=True))


@donors_bp.route('', methods=['POST'])
@donors_bp.route('/', methods=['POST'])
@token_required
@role_required('donor')
def update_donor_profile():
    db = get_db()
    user_id = g.current_user['user_id']
    data = request.get_json() or {}

    fields = []
    params = []
    for key in EDITABLE_FIELDS:
        if key in data:
            value = data[key]
            if key == 'sms_consent':
                value = 1 if value else 0
            elif value == '' and key in ('last_donation_date', 'aadhaar'):
                value = None
            fields.append(f'{key} = %s')
            params.append(value)

    if not fields:
        return jsonify({'error': 'No fields to update'}), 400

    fields.append('updated_at = CURRENT_TIMESTAMP')
    params.append(user_id)
    query = f'UPDATE donors SET {", ".join(fields)} WHERE user_id = %s'
    db.execute(query, params)
    db.commit()

    row = db.execute('SELECT * FROM donors WHERE user_id = %s', (user_id,)).fetchone()
    return jsonify({'message': 'Profile updated', 'donor': _donor_row_to_dict(row, full=True, can_see_phone=True)})


@donors_bp.route('/verify-certificate', methods=['POST'])
@token_required
@role_required('donor')
def verify_certificate_code():
    """Donor enters certificate code to verify donation and increment count"""
    db = get_db()
    user_id = g.current_user['user_id']
    data = request.get_json() or {}
    code = (data.get('certificate_code') or '').strip().upper()

    if not code:
        return jsonify({'error': 'Certificate code required'}), 400

    # Check if code exists in donations table
    donation = db.execute(
        'SELECT * FROM donations WHERE certificate_code = %s', (code,)
    ).fetchone()

    if not donation:
        return jsonify({'error': 'Invalid certificate code'}), 404

    # Check if this code was already used by this donor
    donor = db.execute('SELECT donation_codes, total_units_donated FROM donors WHERE user_id = %s', (user_id,)).fetchone()
    if not donor:
        return jsonify({'error': 'Donor profile not found'}), 404

    try:
        codes = json.loads(donor['donation_codes']) if donor['donation_codes'] else []
    except (json.JSONDecodeError, TypeError):
        codes = []

    if code in codes:
        return jsonify({'error': 'This certificate code was already used', 'already_used': True}), 400

    # Verify the donation belongs to this donor (optional - could allow any valid code)
    # For now, allow any valid code to be claimed once

    codes.append(code)
    new_total = (donor['total_units_donated'] or 0) + (donation['units'] or 1)

    db.execute(
        'UPDATE donors SET donation_codes = %s, total_units_donated = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s',
        (json.dumps(codes), new_total, user_id)
    )
    db.commit()

    return jsonify({
        'message': 'Certificate verified successfully',
        'units_added': donation['units'] or 1,
        'total_units_donated': new_total,
        'certificate_code': code
    })


@donors_bp.route('/top-donors', methods=['GET'])
def top_donors():
    """Get top donors by total units donated - for homepage leaderboard"""
    db = get_db()
    limit = min(int(request.args.get('limit', 10)), 50)

    rows = db.execute('''
        SELECT id, name, blood_group, city, total_units_donated, created_at
        FROM donors
        WHERE total_units_donated > 0
        ORDER BY total_units_donated DESC, created_at ASC
        LIMIT %s
    ''', (limit,)).fetchall()

    return jsonify([dict(r) for r in rows])