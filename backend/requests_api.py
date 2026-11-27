from flask import Blueprint, jsonify, request, g
from matching import alert_donors
from database import get_db
from decorators import token_required, require_role as role_required
from datetime import datetime, date

requests_bp = Blueprint('requests', __name__)

def _request_row_to_dict(row):
    return dict(row)


@requests_bp.route('', methods=['GET'])
@requests_bp.route('/', methods=['GET'])
@token_required
def list_requests():
    db = get_db()
    status = request.args.get('status')
    blood_group = request.args.get('blood_group')
    city = request.args.get('city')

    query = 'SELECT * FROM requests WHERE 1=1'
    params = []
    if status:
        query += ' AND status = ?'
        params.append(status)
    if blood_group:
        query += ' AND blood_group = ?'
        params.append(blood_group)
    if city:
        query += ' AND city = ?'
        params.append(city)

    query += ' ORDER BY '
    query += "CASE priority WHEN 'critical' THEN 0 WHEN 'urgent' THEN 1 ELSE 2 END, created_at DESC"

    rows = db.execute(query, params).fetchall()
    return jsonify([_request_row_to_dict(r) for r in rows])


@requests_bp.route('', methods=['POST'])
@requests_bp.route('/', methods=['POST'])
@token_required
def create_request():
    db = get_db()
    data = request.get_json() or {}

    patient_name = (data.get('patient_name') or '').strip()
    hospital_name = (data.get('hospital_name') or '').strip()
    doctor_id = (data.get('doctor_id') or '').strip()
    nurse_id = (data.get('nurse_id') or '').strip()
    paramedic_id = (data.get('paramedic_id') or '').strip()
    blood_group = data.get('blood_group')
    units_needed = data.get('units_needed', 1)
    priority = data.get('priority', 'normal')
    city = (data.get('city') or '').strip()
    pincode = (data.get('pincode') or '').strip()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not all([patient_name, hospital_name, doctor_id, blood_group]):
        return jsonify({'error': 'patient_name, hospital_name, doctor_id, blood_group required'}), 400

    if blood_group not in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
        return jsonify({'error': 'Invalid blood group'}), 400

    if priority not in ['critical', 'urgent', 'normal']:
        return jsonify({'error': 'Invalid priority'}), 400

    if not isinstance(units_needed, int) or units_needed < 1:
        return jsonify({'error': 'units_needed must be a positive integer'}), 400

    cursor = db.execute(
        '''INSERT INTO requests (requester_id, patient_name, hospital_name, doctor_id, nurse_id, paramedic_id,
               blood_group, units_needed, priority, city, pincode, latitude, longitude)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (g.current_user['user_id'], patient_name, hospital_name, doctor_id, nurse_id, paramedic_id,
         blood_group, units_needed, priority, city, pincode, latitude, longitude)
    )
    request_id = cursor.lastrowid
    db.commit()

    # Auto-verify if requester is staff
    user_role = g.current_user.get('role')
    if user_role in ('admin', 'doctor', 'paramedical', 'nurse', 'blood_connect'):
        db.execute(
            'UPDATE requests SET verified = 1, verified_by = ?, verified_at = CURRENT_TIMESTAMP WHERE id = ?',
            (g.current_user['user_id'], request_id)
        )
        # Create hospital inbox notices
        from hospital import _generate_hospital_id
        # Find hospitals with this blood group in stock
        hospitals = db.execute(
            '''SELECT h.id, h.latitude, h.longitude
               FROM hospitals h
               JOIN hospital_blood_stock hbs ON hbs.hospital_id = h.id
               WHERE hbs.blood_group = ? AND hbs.units_available > 0 AND h.verified = 1''',
            (blood_group,)
        ).fetchall()

        for hosp in hospitals:
            distance = None
            if latitude and longitude and hosp['latitude'] and hosp['longitude']:
                from math import radians, sin, cos, sqrt, atan2
                R = 6371
                dlat = radians(hosp['latitude'] - latitude)
                dlon = radians(hosp['longitude'] - longitude)
                a = sin(dlat/2)**2 + cos(radians(latitude)) * cos(radians(hosp['latitude'])) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = R * c

            db.execute(
                'INSERT INTO request_bank_notices (request_id, blood_bank_id, status, distance_km) VALUES (?, ?, ?, ?)',
                (request_id, hosp['id'], 'notified', round(distance, 1) if distance else None)
            )
        db.commit()

    # Alert matching donors
    try:
        alert_donors(request_id)
    except Exception as e:
        print(f"Alert donors failed: {e}")

    return jsonify({'message': 'Request created', 'request_id': request_id}), 201


@requests_bp.route('/<int:request_id>', methods=['GET'])
@token_required
def get_request(request_id):
    db = get_db()
    row = db.execute('SELECT * FROM requests WHERE id = ?', (request_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Request not found'}), 404

    # Get alerts for this request
    alerts = db.execute(
        '''SELECT a.*, d.name as donor_name, d.phone as donor_phone, d.blood_group as donor_bg
           FROM alerts_sent a JOIN donors d ON d.id = a.donor_id
           WHERE a.request_id = ?''',
        (request_id,)
    ).fetchall()

    result = dict(row)
    result['alerts'] = [dict(a) for a in alerts]
    return jsonify(result)


@requests_bp.route('/<int:request_id>/verify', methods=['POST'])
@token_required
@role_required('admin', 'doctor', 'paramedical', 'nurse', 'blood_connect')
def verify_request(request_id):
    db = get_db()
    row = db.execute('SELECT * FROM requests WHERE id = ?', (request_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Request not found'}), 404

    db.execute(
        'UPDATE requests SET verified = 1, verified_by = ?, verified_at = CURRENT_TIMESTAMP WHERE id = ?',
        (g.current_user['user_id'], request_id)
    )

    # Create hospital inbox notices for hospitals with matching blood group
    blood_group = row['blood_group']
    latitude = row['latitude']
    longitude = row['longitude']

    hospitals = db.execute(
        '''SELECT h.id, h.latitude, h.longitude
           FROM hospitals h
           JOIN hospital_blood_stock hbs ON hbs.hospital_id = h.id
           WHERE hbs.blood_group = ? AND hbs.units_available > 0 AND h.verified = 1''',
        (blood_group,)
    ).fetchall()

    for hosp in hospitals:
        distance = None
        if latitude and longitude and hosp['latitude'] and hosp['longitude']:
            from math import radians, sin, cos, sqrt, atan2
            R = 6371
            dlat = radians(hosp['latitude'] - latitude)
            dlon = radians(hosp['longitude'] - longitude)
            a = sin(dlat/2)**2 + cos(radians(latitude)) * cos(radians(hosp['latitude'])) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c

        db.execute(
            'INSERT INTO request_bank_notices (request_id, blood_bank_id, status, distance_km) VALUES (?, ?, ?, ?)',
            (request_id, hosp['id'], 'notified', round(distance, 1) if distance else None)
        )

    db.commit()

    # Alert matching donors
    try:
        alert_donors(request_id)
    except Exception as e:
        print(f"Alert donors failed: {e}")

    return jsonify({'message': 'Request verified. Donors alerted and hospitals notified.'})


@requests_bp.route('/<int:request_id>', methods=['PUT'])
@token_required
def update_request(request_id):
    db = get_db()
    row = db.execute('SELECT * FROM requests WHERE id = ?', (request_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Request not found'}), 404

    # Only requester or admin can update
    if row['requester_id'] != g.current_user['user_id'] and g.current_user.get('role') != 'admin':
        return jsonify({'error': 'Not authorized'}), 403

    data = request.get_json() or {}
    allowed_fields = ['patient_name', 'hospital_name', 'doctor_id', 'nurse_id', 'paramedic_id',
                      'blood_group', 'units_needed', 'priority', 'city', 'pincode', 'status']

    fields = []
    params = []
    for key in allowed_fields:
        if key in data:
            fields.append(f'{key} = ?')
            params.append(data[key])

    if not fields:
        return jsonify({'error': 'No fields to update'}), 400

    params.append(request_id)
    query = f'UPDATE requests SET {", ".join(fields)} WHERE id = ?'
    db.execute(query, params)
    db.commit()

    return jsonify({'message': 'Request updated'})


@requests_bp.route('/my', methods=['GET'])
@token_required
def my_requests():
    db = get_db()
    rows = db.execute(
        'SELECT * FROM requests WHERE requester_id = ? ORDER BY created_at DESC',
        (g.current_user['user_id'],)
    ).fetchall()
    return jsonify([_request_row_to_dict(r) for r in rows])


# Donor message inbox
@requests_bp.route('/donor-messages/<int:request_id>', methods=['GET'])
@token_required
@role_required('admin')
def donor_messages(request_id):
    """Admin views donor responses/messages for a request"""
    db = get_db()
    messages = db.execute(
        '''SELECT a.*, d.name as donor_name, d.phone as donor_phone, d.blood_group as donor_bg,
                  d.city as donor_city, d.email as donor_email
           FROM alerts_sent a JOIN donors d ON d.id = a.donor_id
           WHERE a.request_id = ?
           ORDER BY a.sent_at DESC''',
        (request_id,)
    ).fetchall()
    return jsonify([dict(m) for m in messages])


@requests_bp.route('/donor-messages/hospital/<int:request_id>', methods=['GET'])
@token_required
@role_required('hospital', 'blood_connect', 'admin', 'doctor', 'paramedical', 'nurse')
def hospital_donor_messages(request_id):
    """Hospital/blood bank views donor responses (with phone numbers)"""
    db = get_db()
    messages = db.execute(
        '''SELECT a.*, d.name as donor_name, d.phone as donor_phone, d.blood_group as donor_bg,
                  d.city as donor_city
           FROM alerts_sent a JOIN donors d ON d.id = a.donor_id
           WHERE a.request_id = ?
           ORDER BY a.sent_at DESC''',
        (request_id,)
    ).fetchall()
    return jsonify([dict(m) for m in messages])


# Donor sends message/response
@requests_bp.route('/donor-message', methods=['POST'])
@token_required
@role_required('donor')
def donor_send_message():
    """Donor sends a message in response to an alert"""
    db = get_db()
    data = request.get_json() or {}
    request_id = data.get('request_id')
    message = (data.get('message') or '').strip()

    if not request_id or not message:
        return jsonify({'error': 'request_id and message required'}), 400

    # Verify this donor has an alert for this request
    donor = db.execute('SELECT id FROM donors WHERE user_id = ?', (g.current_user['user_id'],)).fetchone()
    if not donor:
        return jsonify({'error': 'Donor profile not found'}), 404

    alert = db.execute(
        'SELECT id FROM alerts_sent WHERE request_id = ? AND donor_id = ?',
        (request_id, donor['id'])
    ).fetchone()
    if not alert:
        return jsonify({'error': 'No alert found for this request'}), 404

    # Store message in alerts_sent (we can add a message column or create separate table)
    # For now, update the alert status with message in receiver_notes or similar
    # Let's add a donor_message column to alerts_sent if it doesn't exist
    try:
        db.execute('ALTER TABLE alerts_sent ADD COLUMN donor_message TEXT')
    except:
        pass

    db.execute(
        'UPDATE alerts_sent SET donor_message = ?, responded_at = CURRENT_TIMESTAMP WHERE id = ?',
        (message, alert['id'])
    )
    db.commit()

    return jsonify({'message': 'Message sent to hospital/admin'})


@requests_bp.route('/stats', methods=['GET'])
@token_required
def request_stats():
    db = get_db()
    stats = {}
    stats['total'] = db.execute('SELECT COUNT(*) as c FROM requests').fetchone()['c']
    stats['pending'] = db.execute("SELECT COUNT(*) as c FROM requests WHERE status = 'pending'").fetchone()['c']
    stats['verified'] = db.execute("SELECT COUNT(*) as c FROM requests WHERE verified = 1").fetchone()['c']
    stats['fulfilled'] = db.execute("SELECT COUNT(*) as c FROM requests WHERE status = 'fulfilled'").fetchone()['c']
    stats['critical'] = db.execute("SELECT COUNT(*) as c FROM requests WHERE priority = 'critical'").fetchone()['c']
    stats['by_blood_group'] = {}
    for bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
        count = db.execute("SELECT COUNT(*) as c FROM requests WHERE blood_group = ?", (bg,)).fetchone()['c']
        stats['by_blood_group'][bg] = count
    return jsonify(stats)