from flask import Blueprint, jsonify, request, g
from database import get_db
from auth import token_required, role_required

donors_bp = Blueprint('donors', __name__)

# Returned by the public list / detail endpoints
PUBLIC_FIELDS = [
    'id', 'user_id', 'name', 'blood_group', 'gender', 'age', 'phone',
    'latitude', 'longitude', 'city', 'last_donation_date', 'status',
    'cooldown_months', 'is_rare_group', 'created_at',
]
# Only returned to the donor themselves (/me and after profile update)
PRIVATE_FIELDS = [
    'aadhaar', 'weight', 'previous_hb', 'diseases', 'bad_habits',
    'disorders', 'sms_consent',
]
EDITABLE_FIELDS = [
    'name', 'blood_group', 'gender', 'age', 'phone', 'latitude', 'longitude',
    'city', 'last_donation_date', 'aadhaar', 'weight', 'previous_hb',
    'diseases', 'bad_habits', 'disorders', 'sms_consent',
]


def _donor_row_to_dict(row, full=False):
    fields = PUBLIC_FIELDS + (PRIVATE_FIELDS if full else [])
    available = row.keys()
    return {k: row[k] for k in fields if k in available}


@donors_bp.route('', methods=['GET'])
@donors_bp.route('/', methods=['GET'])
def list_donors():
    db = get_db()
    blood_group = request.args.get('blood_group')
    city = request.args.get('city')
    status = request.args.get('status', 'active')

    query = 'SELECT * FROM donors WHERE status = ?'
    params = [status]
    if blood_group:
        query += ' AND blood_group = ?'
        params.append(blood_group)
    if city:
        query += ' AND city = ?'
        params.append(city)

    rows = db.execute(query, params).fetchall()
    return jsonify([_donor_row_to_dict(r) for r in rows])


@donors_bp.route('/me', methods=['GET'])
@token_required
def donor_me():
    db = get_db()
    user_id = g.current_user['user_id']
    row = db.execute('SELECT * FROM donors WHERE user_id = ?', (user_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Donor profile not found'}), 404
    return jsonify(_donor_row_to_dict(row, full=True))


@donors_bp.route('/<int:donor_id>', methods=['GET'])
def get_donor(donor_id):
    db = get_db()
    row = db.execute('SELECT * FROM donors WHERE id = ?', (donor_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Donor not found'}), 404
    return jsonify(_donor_row_to_dict(row))


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
            fields.append(f'{key} = ?')
            params.append(value)

    if not fields:
        return jsonify({'error': 'No fields to update'}), 400

    fields.append('updated_at = CURRENT_TIMESTAMP')
    params.append(user_id)
    query = f'UPDATE donors SET {", ".join(fields)} WHERE user_id = ?'
    db.execute(query, params)
    db.commit()

    row = db.execute('SELECT * FROM donors WHERE user_id = ?', (user_id,)).fetchone()
    return jsonify({'message': 'Profile updated', 'donor': _donor_row_to_dict(row, full=True)})