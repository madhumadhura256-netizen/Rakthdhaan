import traceback

from flask import Blueprint, jsonify, request, g

from database import get_db
from decorators import token_required, can_verify_request
from matching import alert_donors
from routing import notify_banks, stock_summary, routing_message

requests_bp = Blueprint('requests', __name__)

BLOOD_GROUPS = {'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'}


def _request_row_to_dict(row):
    return {
        'id': row['id'],
        'requester_id': row['requester_id'],
        'patient_name': row['patient_name'],
        'hospital_name': row['hospital_name'],
        'doctor_id': row['doctor_id'],
        'blood_group': row['blood_group'],
        'units_needed': row['units_needed'],
        'priority': row['priority'],
        'status': row['status'],
        'latitude': row['latitude'],
        'longitude': row['longitude'],
        'city': row['city'],
        'pincode': row['pincode'],
        'verified': row['verified'],
        'verified_by': row['verified_by'],
        'verified_at': row['verified_at'],
        'created_at': row['created_at'],
    }


@requests_bp.route('', methods=['GET'])
@requests_bp.route('/', methods=['GET'])
@token_required
def list_requests():
    db = get_db()
    status = request.args.get('status')
    priority = request.args.get('priority')
    blood_group = request.args.get('blood_group')

    query = 'SELECT * FROM requests WHERE 1=1'
    params = []
    if status:
        query += ' AND status = ?'
        params.append(status)
    if priority:
        query += ' AND priority = ?'
        params.append(priority)
    if blood_group:
        query += ' AND blood_group = ?'
        params.append(blood_group)

    # Critical first, then urgent, then normal; newest first inside each group
    query += (
        " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'urgent' THEN 1 ELSE 2 END,"
        " created_at DESC"
    )

    rows = db.execute(query, params).fetchall()
    return jsonify([_request_row_to_dict(r) for r in rows])


@requests_bp.route('/<int:request_id>', methods=['GET'])
@token_required
def get_request(request_id):
    db = get_db()
    row = db.execute('SELECT * FROM requests WHERE id = ?', (request_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Request not found'}), 404
    return jsonify(_request_row_to_dict(row))


@requests_bp.route('', methods=['POST'])
@requests_bp.route('/', methods=['POST'])
@token_required
def create_request():
    db = get_db()
    user_id = g.current_user['user_id']
    data = request.get_json() or {}

    patient_name = (data.get('patient_name') or '').strip()
    hospital_name = (data.get('hospital_name') or '').strip()
    doctor_id = (data.get('doctor_id') or '').strip()
    blood_group = data.get('blood_group')
    priority = data.get('priority', 'normal')
    city = data.get('city')
    pincode = data.get('pincode')

    if not all([patient_name, hospital_name, doctor_id, blood_group]):
        return jsonify({'error': 'patient_name, hospital_name, doctor_id, blood_group are required'}), 400
    if blood_group not in BLOOD_GROUPS:
        return jsonify({'error': 'Invalid blood group'}), 400
    if priority not in ('critical', 'urgent', 'normal'):
        return jsonify({'error': 'priority must be critical, urgent, or normal'}), 400

    try:
        units_needed = int(data.get('units_needed', 1))
    except (TypeError, ValueError):
        return jsonify({'error': 'units_needed must be a number'}), 400
    if units_needed < 1:
        return jsonify({'error': 'units_needed must be at least 1'}), 400

    try:
        latitude = float(data['latitude']) if data.get('latitude') not in (None, '') else None
        longitude = float(data['longitude']) if data.get('longitude') not in (None, '') else None
    except (TypeError, ValueError):
        return jsonify({'error': 'latitude and longitude must be numbers'}), 400

    cursor = db.execute(
        '''INSERT INTO requests
           (requester_id, patient_name, hospital_name, doctor_id, blood_group, units_needed,
            priority, latitude, longitude, city, pincode)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (user_id, patient_name, hospital_name, doctor_id, blood_group, units_needed,
         priority, latitude, longitude, city, pincode)
    )
    db.commit()
    new_id = cursor.lastrowid
    row = db.execute('SELECT * FROM requests WHERE id = ?', (new_id,)).fetchone()
    req = _request_row_to_dict(row)

    # Send the request to the nearest blood banks and check their stock
    notify_banks(db, req)
    summary = stock_summary(db, req)
    return jsonify({'message': routing_message(req, summary), 'request': req}), 201
@requests_bp.route('/<int:request_id>/verify', methods=['POST'])
@token_required
@can_verify_request
def verify_request(request_id):
    """Only admin, doctor, paramedical, blood_connect can verify requests"""
    db = get_db()
    data = request.get_json() or {}
    verified_by = data.get('verified_by', g.current_user.get('email', ''))

    row = db.execute('SELECT * FROM requests WHERE id = ?', (request_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Request not found'}), 404

    if row['verified']:
        return jsonify({'error': 'Request already verified'}), 400

    db.execute(
        'UPDATE requests SET verified = 1, verified_by = ?, verified_at = CURRENT_TIMESTAMP WHERE id = ?',
        (verified_by, request_id)
    )
    db.execute(
        "UPDATE donors SET status = 'active' "
        "WHERE status = 'inactive' AND next_eligible_date IS NOT NULL "
        "AND next_eligible_date <= date('now')"
    )
    db.commit()

    # Routing must never undo the verification
    try:
        req = _request_row_to_dict(row)
        notify_banks(db, req)          # covers older requests that were never routed
        summary = stock_summary(db, req)
        in_stock = [s for s in summary if s['enough']]

        if in_stock:
            names = ', '.join(s['name'] for s in in_stock[:3])
            return jsonify({'message': (
                f"Request verified. {names} already has {req['blood_group']} in stock, "
                f"so donors were not alerted."
            )})

        place = summary[0]['name'] if summary else req['hospital_name']
        donors = [dict(d) for d in db.execute('SELECT * FROM donors').fetchall()]
        alerted = alert_donors(db, req, donors, place=place)
        return jsonify({'message': (
            f"Request verified. No nearby blood bank has enough {req['blood_group']}, "
            f"so {alerted} donors were alerted to donate at {place}."
        )})
    except Exception:
        traceback.print_exc()
        return jsonify({'message': 'Request verified, but routing failed. See the server terminal.'})