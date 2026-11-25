from flask import Blueprint, jsonify, request, g

from database import get_db
from auth import token_required, role_required

hospital_bp = Blueprint('hospital', __name__)

STAFF = ('admin', 'doctor', 'paramedical', 'blood_connect')


def _owns_bank(db, user, blood_bank_id):
    """Admins see everything; bank staff only their own bank."""
    if user.get('role') == 'admin':
        return True
    row = db.execute('SELECT user_id FROM blood_banks WHERE id = ?', (blood_bank_id,)).fetchone()
    return bool(row) and row['user_id'] == user['user_id']


# ---------------- Hospital / blood bank side ----------------

@hospital_bp.route('/inbox', methods=['GET'])
@token_required
@role_required(*STAFF)
def inbox():
    db = get_db()
    user = g.current_user

    sql = '''
        SELECT n.id AS notice_id, n.status AS notice_status, n.distance_km, n.blood_bank_id,
               b.name AS bank_name,
               r.id AS request_id, r.patient_name, r.hospital_name, r.blood_group,
               r.units_needed, r.priority, r.status AS request_status, r.verified,
               r.city, r.created_at,
               COALESCE(s.units_available, 0) AS units_in_stock
        FROM request_bank_notices n
        JOIN blood_banks b ON b.id = n.blood_bank_id
        JOIN requests r ON r.id = n.request_id
        LEFT JOIN blood_stock s
               ON s.blood_bank_id = n.blood_bank_id AND s.blood_group = r.blood_group
    '''
    params = []
    if user.get('role') != 'admin':
        sql += ' WHERE b.user_id = ?'
        params.append(user['user_id'])
    sql += (" ORDER BY CASE r.priority WHEN 'critical' THEN 0 WHEN 'urgent' THEN 1 ELSE 2 END,"
            " r.created_at DESC")

    result = []
    for row in db.execute(sql, params).fetchall():
        item = dict(row)
        donors = db.execute(
            "SELECT d.id, d.name, d.blood_group, d.phone "
            "FROM alerts_sent a JOIN donors d ON d.id = a.donor_id "
            "WHERE a.request_id = ? AND a.status = 'accepted'",
            (row['request_id'],),
        ).fetchall()
        item['accepted_donors'] = [dict(d) for d in donors]
        result.append(item)

    return jsonify(result)


@hospital_bp.route('/notices/<int:notice_id>/respond', methods=['POST'])
@token_required
@role_required(*STAFF)
def respond_notice(notice_id):
    db = get_db()
    response = (request.get_json() or {}).get('response')
    if response not in ('accepted', 'declined', 'fulfilled'):
        return jsonify({'error': 'response must be accepted, declined or fulfilled'}), 400

    notice = db.execute(
        'SELECT * FROM request_bank_notices WHERE id = ?', (notice_id,)
    ).fetchone()
    if not notice:
        return jsonify({'error': 'Notice not found'}), 404
    if not _owns_bank(db, g.current_user, notice['blood_bank_id']):
        return jsonify({'error': 'This request was sent to a different blood bank'}), 403

    db.execute(
        'UPDATE request_bank_notices SET status = ?, responded_at = CURRENT_TIMESTAMP WHERE id = ?',
        (response, notice_id),
    )
    if response == 'fulfilled':
        db.execute("UPDATE requests SET status = 'fulfilled' WHERE id = ?", (notice['request_id'],))
    db.commit()
    return jsonify({'message': f'Marked as {response}.'})


# ---------------- Donor side ----------------

@hospital_bp.route('/my-alerts', methods=['GET'])
@token_required
@role_required('donor')
def my_alerts():
    db = get_db()
    rows = db.execute('''
        SELECT a.id AS alert_id, a.status, a.sent_at,
               r.id AS request_id, r.blood_group, r.units_needed, r.priority,
               r.hospital_name, r.city,
               (SELECT b.name
                  FROM request_bank_notices n
                  JOIN blood_banks b ON b.id = n.blood_bank_id
                 WHERE n.request_id = r.id
                 ORDER BY n.distance_km IS NULL, n.distance_km
                 LIMIT 1) AS donate_at
        FROM alerts_sent a
        JOIN requests r ON r.id = a.request_id
        JOIN donors d ON d.id = a.donor_id
        WHERE d.user_id = ?
        ORDER BY a.sent_at DESC
    ''', (g.current_user['user_id'],)).fetchall()
    return jsonify([dict(r) for r in rows])


@hospital_bp.route('/my-alerts/<int:alert_id>/respond', methods=['POST'])
@token_required
@role_required('donor')
def respond_alert(alert_id):
    db = get_db()
    response = (request.get_json() or {}).get('response')
    if response not in ('accepted', 'declined'):
        return jsonify({'error': 'response must be accepted or declined'}), 400

    row = db.execute(
        'SELECT a.id, d.status AS donor_status '
        'FROM alerts_sent a JOIN donors d ON d.id = a.donor_id '
        'WHERE a.id = ? AND d.user_id = ?',
        (alert_id, g.current_user['user_id']),
    ).fetchone()
    if not row:
        return jsonify({'error': 'Alert not found'}), 404

    if response == 'accepted' and row['donor_status'] != 'active':
        return jsonify({'error': 'You are in your rest period and cannot donate right now.'}), 400

    db.execute(
        'UPDATE alerts_sent SET status = ?, responded_at = CURRENT_TIMESTAMP WHERE id = ?',
        (response, alert_id),
    )
    db.commit()

    if response == 'accepted':
        return jsonify({'message': 'Thank you! The blood bank can now see that you are coming.'})
    return jsonify({'message': 'Response saved.'})