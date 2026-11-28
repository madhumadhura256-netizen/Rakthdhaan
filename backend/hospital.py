from datetime import date
from math import radians, sin, cos, sqrt, atan2

from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, request, g

from database import get_db
from auth import token_required, role_required
from sms import send_sms

hospital_bp = Blueprint('hospital', __name__)

STAFF = ('admin', 'doctor', 'paramedical', 'blood_connect', 'nurse')
INBOX_ROLES = STAFF + ('hospital',)
ADMIN_ROLE = ('admin',)

_columns_checked = False


def _ensure_columns(db):
    """Add optional columns once per process instead of on every request."""
    global _columns_checked
    if _columns_checked:
        return
    for stmt in (
        'ALTER TABLE alerts_sent ADD COLUMN donor_message TEXT',
        'ALTER TABLE alerts_sent ADD COLUMN hospital_reply TEXT',
        'ALTER TABLE alerts_sent ADD COLUMN replied_at TIMESTAMP',
    ):
        try:
            db.execute(stmt)
            db.commit()
        except Exception:
            pass  # column already exists
    _columns_checked = True


def _owns_hospital(db, user, hospital_id):
    """Admins see everything; hospital staff only their own hospital."""
    if user.get('role') == 'admin':
        return True
    row = db.execute('SELECT user_id FROM hospitals WHERE id = %s', (hospital_id,)).fetchone()
    return bool(row) and row['user_id'] == user['user_id']


def _has_access_to_request(db, user, request_id):
    """True if the user's hospital received a notice for this request (admin: always)."""
    notices = db.execute(
        'SELECT blood_bank_id FROM request_bank_notices WHERE request_id = %s',
        (request_id,)
    ).fetchall()
    if not notices:
        return None  # no notice exists at all
    return any(_owns_hospital(db, user, n['blood_bank_id']) for n in notices)


def _generate_hospital_id(db):
    """Generate next hospital ID like HOSP-0001"""
    row = db.execute("SELECT hospital_id FROM hospitals ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return "HOSP-0001"
    last = row['hospital_id']
    try:
        num = int(last.split('-')[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f"HOSP-{num:04d}"


def _haversine(lat1, lon1, lat2, lon2):
    """Distance in km between two lat/lon points"""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# ==================== HOSPITAL REGISTRATION ====================

@hospital_bp.route('/register', methods=['POST'])
@token_required
def register_hospital():
    """Hospital registers - creates hospital profile for the logged-in user"""
    db = get_db()
    user = g.current_user

    existing = db.execute('SELECT id FROM hospitals WHERE user_id = %s', (user['user_id'],)).fetchone()
    if existing:
        return jsonify({'error': 'Hospital profile already exists for this user'}), 409

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    address = (data.get('address') or '').strip()
    city = (data.get('city') or '').strip()
    pincode = (data.get('pincode') or '').strip()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    phone = (data.get('phone') or '').strip()
    email = (data.get('email') or '').strip().lower()
    license_number = (data.get('license_number') or '').strip()
    license_document = data.get('license_document')  # base64 or path

    if not all([name, address, city, pincode, phone, email, license_number]):
        return jsonify({'error': 'All fields are required'}), 400

    # 0 is a valid coordinate, so check for None instead of falsiness
    if latitude is None or longitude is None:
        return jsonify({'error': 'Latitude and longitude required'}), 400

    hospital_id = _generate_hospital_id(db)

    db.execute(
        '''INSERT INTO hospitals (user_id, hospital_id, name, address, city, pincode,
               latitude, longitude, phone, email, license_number, license_document)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
        (user['user_id'], hospital_id, name, address, city, pincode,
         latitude, longitude, phone, email, license_number, license_document)
    )
    db.commit()

    return jsonify({
        'message': 'Hospital registration submitted for verification',
        'hospital_id': hospital_id,
        'status': 'pending_verification'
    }), 201


@hospital_bp.route('/my-profile', methods=['GET'])
@token_required
@role_required('hospital')
def my_hospital_profile():
    """Hospital views their own profile"""
    db = get_db()
    row = db.execute('SELECT * FROM hospitals WHERE user_id = %s', (g.current_user['user_id'],)).fetchone()
    if not row:
        return jsonify({'error': 'Hospital profile not found'}), 404
    return jsonify(dict(row))


# ==================== ADMIN VERIFICATION ====================

@hospital_bp.route('/admin/pending', methods=['GET'])
@token_required
@role_required(*ADMIN_ROLE)
def admin_pending_hospitals():
    """Admin sees all pending hospital verifications"""
    db = get_db()
    rows = db.execute('''
        SELECT h.*, u.email as user_email, u.phone as user_phone
        FROM hospitals h
        JOIN users u ON u.id = h.user_id
        WHERE h.verified = 0
        ORDER BY h.created_at DESC
    ''').fetchall()
    return jsonify([dict(r) for r in rows])


@hospital_bp.route('/admin/<int:hospital_id>/verify', methods=['POST'])
@token_required
@role_required(*ADMIN_ROLE)
def admin_verify_hospital(hospital_id):
    """Admin verifies or rejects a hospital"""
    db = get_db()
    data = request.get_json() or {}
    verified = data.get('verified', True)
    notes = data.get('notes', '')

    hospital = db.execute('SELECT * FROM hospitals WHERE id = %s', (hospital_id,)).fetchone()
    if not hospital:
        return jsonify({'error': 'Hospital not found'}), 404

    if verified:
        db.execute(
            'UPDATE hospitals SET verified = 1, verified_by = %s, verified_at = CURRENT_TIMESTAMP, '
            'verification_notes = %s WHERE id = %s',
            (g.current_user['user_id'], notes, hospital_id)
        )
        db.execute(
            'UPDATE users SET verified = 1, verified_by = %s, verified_at = CURRENT_TIMESTAMP WHERE id = %s',
            (g.current_user['user_id'], hospital['user_id'])
        )
        msg = 'Hospital verified successfully'
    else:
        db.execute(
            'UPDATE hospitals SET verified = 0, verification_notes = %s WHERE id = %s',
            (notes, hospital_id)
        )
        msg = 'Hospital verification rejected'

    db.commit()
    return jsonify({'message': msg})


@hospital_bp.route('/admin/all', methods=['GET'])
@token_required
@role_required(*ADMIN_ROLE)
def admin_all_hospitals():
    """Admin sees all hospitals with verification status"""
    db = get_db()
    rows = db.execute('''
        SELECT h.*, u.email as user_email
        FROM hospitals h
        JOIN users u ON u.id = h.user_id
        ORDER BY h.verified DESC, h.created_at DESC
    ''').fetchall()
    return jsonify([dict(r) for r in rows])


# ==================== HOSPITAL BLOOD STOCK MANAGEMENT ====================

@hospital_bp.route('/stock', methods=['GET'])
@token_required
@role_required('hospital', 'admin')
def get_hospital_stock():
    """Hospital views their blood stock"""
    db = get_db()
    user = g.current_user

    if user['role'] == 'admin':
        hospital_id = request.args.get('hospital_id')
        if not hospital_id:
            return jsonify({'error': 'hospital_id required for admin'}), 400
    else:
        hospital = db.execute('SELECT id FROM hospitals WHERE user_id = %s', (user['user_id'],)).fetchone()
        if not hospital:
            return jsonify({'error': 'Hospital profile not found'}), 404
        hospital_id = hospital['id']

    rows = db.execute(
        'SELECT * FROM hospital_blood_stock WHERE hospital_id = %s ORDER BY blood_group',
        (hospital_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@hospital_bp.route('/stock', methods=['POST'])
@token_required
@role_required('hospital', 'admin')
def update_hospital_stock():
    """Hospital updates their blood stock"""
    db = get_db()
    user = g.current_user
    data = request.get_json() or {}

    blood_group = data.get('blood_group')
    units_available = data.get('units_available')

    if not blood_group or units_available is None:
        return jsonify({'error': 'blood_group and units_available required'}), 400

    # validate type so a string doesn't crash the comparison
    try:
        units_available = int(units_available)
    except (TypeError, ValueError):
        return jsonify({'error': 'units_available must be a number'}), 400

    if units_available < 0:
        return jsonify({'error': 'units_available cannot be negative'}), 400

    if user['role'] == 'admin':
        hospital_id = data.get('hospital_id')
        if not hospital_id:
            return jsonify({'error': 'hospital_id required for admin'}), 400
    else:
        hospital = db.execute('SELECT id FROM hospitals WHERE user_id = %s', (user['user_id'],)).fetchone()
        if not hospital:
            return jsonify({'error': 'Hospital profile not found'}), 404
        hospital_id = hospital['id']

    existing = db.execute(
        'SELECT id FROM hospital_blood_stock WHERE hospital_id = %s AND blood_group = %s',
        (hospital_id, blood_group)
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE hospital_blood_stock SET units_available = %s, last_updated = CURRENT_TIMESTAMP WHERE id = %s',
            (units_available, existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO hospital_blood_stock (hospital_id, blood_group, units_available) VALUES (%s, %s, %s)',
            (hospital_id, blood_group, units_available)
        )
    db.commit()
    return jsonify({'message': 'Hospital stock updated successfully'})


@hospital_bp.route('/stock/availability', methods=['GET'])
@token_required
@role_required('hospital', 'admin', 'blood_connect', 'doctor', 'paramedical', 'nurse')
def check_blood_availability():
    """Check blood availability across hospitals and blood banks for a blood group"""
    db = get_db()
    blood_group = request.args.get('blood_group')
    city = request.args.get('city')

    if not blood_group:
        return jsonify({'error': 'blood_group required'}), 400

    result = {'hospitals': [], 'blood_banks': []}

    query = '''
        SELECT h.hospital_id, h.name, h.city, h.phone, h.latitude, h.longitude,
               hbs.units_available, hbs.last_updated
        FROM hospital_blood_stock hbs
        JOIN hospitals h ON h.id = hbs.hospital_id
        WHERE hbs.blood_group = %s AND hbs.units_available > 0 AND h.verified = 1
    '''
    params = [blood_group]
    if city:
        query += ' AND h.city = %s'
        params.append(city)
    query += ' ORDER BY hbs.units_available DESC'
    result['hospitals'] = [dict(r) for r in db.execute(query, params).fetchall()]

    query2 = '''
        SELECT b.id as bank_id, b.name, b.city, b.phone, b.latitude, b.longitude,
               bs.units_available, bs.last_updated
        FROM blood_stock bs
        JOIN blood_banks b ON b.id = bs.blood_bank_id
        WHERE bs.blood_group = %s AND bs.units_available > 0
    '''
    params2 = [blood_group]
    if city:
        query2 += ' AND b.city = %s'
        params2.append(city)
    query2 += ' ORDER BY bs.units_available DESC'
    result['blood_banks'] = [dict(r) for r in db.execute(query2, params2).fetchall()]

    return jsonify(result)


# ==================== HOSPITAL INBOX (BLOOD REQUESTS) ====================

@hospital_bp.route('/inbox', methods=['GET'])
@token_required
@role_required(*INBOX_ROLES)
def inbox():
    db = get_db()
    user = g.current_user

    sql = '''
        SELECT n.id AS notice_id, n.status AS notice_status, n.distance_km, n.blood_bank_id,
               b.name AS bank_name,
               r.id AS request_id, r.patient_name, r.hospital_name, r.blood_group,
               r.units_needed, r.priority, r.status AS request_status, r.verified,
               r.city, r.created_at,
               r.doctor_id, r.nurse_id, r.paramedic_id,
               COALESCE(hbs.units_available, 0) AS units_in_stock
        FROM request_bank_notices n
        JOIN hospitals b ON b.id = n.blood_bank_id
        JOIN requests r ON r.id = n.request_id
        LEFT JOIN hospital_blood_stock hbs
               ON hbs.hospital_id = n.blood_bank_id AND hbs.blood_group = r.blood_group
    '''
    params = []
    if user.get('role') != 'admin':
        sql += ' WHERE b.user_id = %s'
        params.append(user['user_id'])
    sql += (" ORDER BY CASE r.priority WHEN 'critical' THEN 0 WHEN 'urgent' THEN 1 ELSE 2 END,"
            " r.created_at DESC")

    result = []
    for row in db.execute(sql, params).fetchall():
        item = dict(row)
        donors = db.execute(
            "SELECT d.id, d.name, d.blood_group, d.phone "
            "FROM alerts_sent a JOIN donors d ON d.id = a.donor_id "
            "WHERE a.request_id = %s AND a.status = 'accepted'",
            (row['request_id'],),
        ).fetchall()
        item['accepted_donors'] = [dict(d) for d in donors]
        result.append(item)

    return jsonify(result)


@hospital_bp.route('/notices/<int:notice_id>/respond', methods=['POST'])
@token_required
@role_required(*INBOX_ROLES)
def respond_notice(notice_id):
    db = get_db()
    response = (request.get_json() or {}).get('response')
    if response not in ('accepted', 'declined', 'fulfilled'):
        return jsonify({'error': 'response must be accepted, declined or fulfilled'}), 400

    notice = db.execute(
        'SELECT * FROM request_bank_notices WHERE id = %s', (notice_id,)
    ).fetchone()
    if not notice:
        return jsonify({'error': 'Notice not found'}), 404
    if not _owns_hospital(db, g.current_user, notice['blood_bank_id']):
        return jsonify({'error': 'This request was sent to a different hospital'}), 403

    db.execute(
        'UPDATE request_bank_notices SET status = %s, responded_at = CURRENT_TIMESTAMP WHERE id = %s',
        (response, notice_id),
    )
    if response == 'fulfilled':
        db.execute("UPDATE requests SET status = 'fulfilled' WHERE id = %s", (notice['request_id'],))
    db.commit()
    return jsonify({'message': f'Marked as {response}.'})


# ==================== DONOR ALERTS (DONOR SIDE) ====================

@hospital_bp.route('/my-alerts', methods=['GET'])
@token_required
@role_required('donor')
def donor_my_alerts():
    """Donor sees requests that were sent to their blood group"""
    db = get_db()
    donor = db.execute('SELECT id FROM donors WHERE user_id = %s',
                       (g.current_user['user_id'],)).fetchone()
    if not donor:
        return jsonify({'error': 'Donor profile not found'}), 404

    _ensure_columns(db)

    rows = db.execute(
        '''SELECT a.id AS alert_id, a.status, a.donor_message,
                  r.id AS request_id, r.blood_group, r.priority, r.city,
                  r.hospital_name, r.hospital_name AS donate_at
           FROM alerts_sent a
           JOIN requests r ON r.id = a.request_id
           WHERE a.donor_id = %s
           ORDER BY a.id DESC''',
        (donor['id'],)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@hospital_bp.route('/my-alerts/<int:alert_id>/respond', methods=['POST'])
@token_required
@role_required('donor')
def donor_respond_alert(alert_id):
    """Donor accepts or declines an alert and optionally sends a message"""
    db = get_db()
    _ensure_columns(db)

    data = request.get_json() or {}
    response = data.get('response')
    message = (data.get('message') or '').strip()[:500]

    if response not in ('accepted', 'declined'):
        return jsonify({'error': 'response must be accepted or declined'}), 400

    donor = db.execute('SELECT id FROM donors WHERE user_id = %s',
                       (g.current_user['user_id'],)).fetchone()
    if not donor:
        return jsonify({'error': 'Donor profile not found'}), 404

    alert = db.execute('SELECT id FROM alerts_sent WHERE id = %s AND donor_id = %s',
                       (alert_id, donor['id'])).fetchone()
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404

    db.execute(
        'UPDATE alerts_sent SET status = %s, donor_message = %s WHERE id = %s',
        (response, message or None, alert_id)
    )
    db.commit()
    return jsonify({'message': 'Your response was sent to the hospital.'})


# ==================== BULK SMS TO NEARBY DONORS ====================

@hospital_bp.route('/send-sms', methods=['POST'])
@token_required
@role_required('hospital', 'admin')
def send_bulk_sms():
    """Hospital sends SMS to all nearby eligible donors of a specific blood group"""
    db = get_db()
    user = g.current_user
    data = request.get_json() or {}

    blood_group = data.get('blood_group')
    custom_message = data.get('message')

    try:
        radius_km = float(data.get('radius_km', 20))
    except (TypeError, ValueError):
        return jsonify({'error': 'radius_km must be a number'}), 400

    if not blood_group:
        return jsonify({'error': 'blood_group required'}), 400

    if user['role'] == 'admin':
        hospital_id = data.get('hospital_id')
        if not hospital_id:
            return jsonify({'error': 'hospital_id required for admin'}), 400
        hospital = db.execute('SELECT * FROM hospitals WHERE hospital_id = %s', (hospital_id,)).fetchone()
    else:
        hospital = db.execute('SELECT * FROM hospitals WHERE user_id = %s', (user['user_id'],)).fetchone()

    if not hospital:
        return jsonify({'error': 'Hospital not found'}), 404
    if not hospital['verified']:
        return jsonify({'error': 'Hospital not verified yet'}), 403
    if hospital['latitude'] is None or hospital['longitude'] is None:
        return jsonify({'error': 'Hospital location is missing'}), 400

    donors = db.execute('''
        SELECT d.id, d.name, d.phone, d.latitude, d.longitude, d.city,
               d.status, d.sms_consent, d.last_donation_date, d.cooldown_months, d.gender
        FROM donors d
        WHERE d.blood_group = %s
        AND d.sms_consent = 1
        AND d.mobile_verified = 1
        AND d.status = 'active'
    ''', (blood_group,)).fetchall()

    nearby = []
    for row in donors:
        donor = dict(row)  # sqlite3.Row does not allow item assignment
        if donor['latitude'] is None or donor['longitude'] is None:
            continue

        dist = _haversine(hospital['latitude'], hospital['longitude'],
                          donor['latitude'], donor['longitude'])
        if dist > radius_km:
            continue

        # Skip donors still in cooldown
        if donor['last_donation_date']:
            months = donor['cooldown_months'] or (3 if donor['gender'] == 'Male' else 4)
            try:
                last = date.fromisoformat(donor['last_donation_date'])
                if last + relativedelta(months=months) > date.today():
                    continue
            except ValueError:
                pass

        donor['distance_km'] = round(dist, 1)
        nearby.append(donor)

    if not nearby:
        return jsonify({'message': 'No eligible donors found nearby', 'sent': 0})

    sent_count = 0
    failed = []
    default_msg = (f"URGENT: {hospital['name']} needs {blood_group} blood donors. "
                   f"Please contact {hospital['phone']} to donate. - Raktdhan")
    message = custom_message or default_msg

    for donor in nearby:
        try:
            send_sms(donor['phone'].replace('+91', '').replace(' ', ''), message)
            sent_count += 1
        except Exception as e:
            failed.append({'donor_id': donor['id'], 'error': str(e)})

    db.execute(
        '''INSERT INTO hospital_sms_log (hospital_id, blood_group, donors_count, message, sent_by, status)
           VALUES (%s, %s, %s, %s, %s, %s)''',
        (hospital['id'], blood_group, sent_count, message, user['user_id'],
         'sent' if not failed else 'partial')
    )
    db.commit()

    return jsonify({
        'message': f'SMS sent to {sent_count} nearby donors',
        'sent': sent_count,
        'failed': len(failed),
        'total_eligible': len(nearby)
    })


@hospital_bp.route('/sms-history', methods=['GET'])
@token_required
@role_required('hospital', 'admin')
def sms_history():
    """Hospital views their SMS sending history"""
    db = get_db()
    user = g.current_user

    if user['role'] == 'admin':
        hospital_id = request.args.get('hospital_id')
        if not hospital_id:
            return jsonify({'error': 'hospital_id required for admin'}), 400
        hospital = db.execute('SELECT id FROM hospitals WHERE hospital_id = %s', (hospital_id,)).fetchone()
    else:
        hospital = db.execute('SELECT id FROM hospitals WHERE user_id = %s', (user['user_id'],)).fetchone()

    if not hospital:
        return jsonify({'error': 'Hospital not found'}), 404

    rows = db.execute(
        'SELECT * FROM hospital_sms_log WHERE hospital_id = %s ORDER BY sent_at DESC LIMIT 50',
        (hospital['id'],)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ==================== NEARBY DONORS LIST ====================

@hospital_bp.route('/nearby-donors', methods=['GET'])
@token_required
@role_required('hospital', 'admin', 'blood_connect', 'doctor', 'paramedical', 'nurse')
def nearby_donors():
    """Get nearby donors for a blood group.
    All roles allowed on this route are trusted staff, so full phone numbers are returned."""
    db = get_db()
    user = g.current_user
    blood_group = request.args.get('blood_group')
    city = request.args.get('city')

    try:
        radius_km = float(request.args.get('radius_km', 20))
    except (TypeError, ValueError):
        return jsonify({'error': 'radius_km must be a number'}), 400

    if not blood_group:
        return jsonify({'error': 'blood_group required'}), 400

    # Reference location (hospital accounts, or admin who passes hospital_id)
    lat, lon = None, None
    if user['role'] == 'hospital':
        hospital = db.execute('SELECT latitude, longitude FROM hospitals WHERE user_id = %s',
                              (user['user_id'],)).fetchone()
        if hospital:
            lat, lon = hospital['latitude'], hospital['longitude']
    elif user['role'] == 'admin':
        hospital_id = request.args.get('hospital_id')
        if hospital_id:
            hospital = db.execute('SELECT latitude, longitude FROM hospitals WHERE hospital_id = %s',
                                  (hospital_id,)).fetchone()
            if hospital:
                lat, lon = hospital['latitude'], hospital['longitude']

    query = '''
        SELECT d.id, d.name, d.blood_group, d.gender, d.age, d.phone, d.city,
               d.latitude, d.longitude, d.status, d.last_donation_date, d.cooldown_months,
               d.total_units_donated, d.created_at
        FROM donors d
        WHERE d.blood_group = %s
        AND d.sms_consent = 1
        AND d.mobile_verified = 1
        AND d.status = 'active'
    '''
    params = [blood_group]
    if city:
        query += ' AND d.city = %s'
        params.append(city)

    nearby = []
    for r in db.execute(query, params).fetchall():
        row = dict(r)
        has_coords = (lat is not None and lon is not None
                      and row['latitude'] is not None and row['longitude'] is not None)
        if has_coords:
            dist = _haversine(lat, lon, row['latitude'], row['longitude'])
            if dist > radius_km:
                continue
            row['distance_km'] = round(dist, 1)
        else:
            row['distance_km'] = None
        nearby.append(row)

    nearby.sort(key=lambda x: x['distance_km'] if x['distance_km'] is not None else 9999)
    return jsonify(nearby)


# ==================== REPLY TO DONOR ====================

@hospital_bp.route('/reply-donor', methods=['POST'])
@token_required
@role_required('hospital', 'admin', 'blood_connect', 'doctor', 'paramedical', 'nurse')
def reply_donor():
    """Hospital staff replies to a donor"""
    db = get_db()
    data = request.get_json() or {}
    request_id = data.get('request_id')
    donor_id = data.get('donor_id')
    message = (data.get('message') or '').strip()

    if not all([request_id, donor_id, message]):
        return jsonify({'error': 'request_id, donor_id, and message required'}), 400

    # ownership check - only a hospital that received this request may reply
    access = _has_access_to_request(db, g.current_user, request_id)
    if access is None:
        return jsonify({'error': 'No notice found for this request'}), 404
    if not access:
        return jsonify({'error': 'This request was sent to a different hospital'}), 403

    donor = db.execute('SELECT * FROM donors WHERE id = %s', (donor_id,)).fetchone()
    if not donor:
        return jsonify({'error': 'Donor not found'}), 404

    _ensure_columns(db)

    db.execute(
        'UPDATE alerts_sent SET hospital_reply = %s, replied_at = CURRENT_TIMESTAMP '
        'WHERE request_id = %s AND donor_id = %s',
        (message, request_id, donor_id)
    )
    db.commit()

    try:
        send_sms(donor['phone'].replace('+91', '').replace(' ', ''),
                 f"Raktdhan: Hospital reply - {message}")
    except Exception as e:
        print(f"SMS failed: {e}")

    return jsonify({'message': 'Reply sent to donor'})


# ==================== DONOR MESSAGES FOR HOSPITAL ====================

@hospital_bp.route('/donor-messages/<int:request_id>', methods=['GET'])
@token_required
@role_required('hospital', 'admin', 'blood_connect', 'doctor', 'paramedical', 'nurse')
def hospital_donor_messages(request_id):
    """Hospital views donor responses/messages for a request.
    Only donors who actually responded (accepted/declined) or left a message are returned."""
    db = get_db()

    access = _has_access_to_request(db, g.current_user, request_id)
    if access is None:
        return jsonify({'error': 'No notice found for this request'}), 404
    if not access:
        return jsonify({'error': 'This request was sent to a different hospital'}), 403

    _ensure_columns(db)

    messages = db.execute(
        '''SELECT a.*, d.name AS donor_name, d.phone AS donor_phone,
                  d.blood_group AS donor_bg, d.city AS donor_city
           FROM alerts_sent a
           JOIN donors d ON d.id = a.donor_id
           WHERE a.request_id = %s
             AND (a.status IN ('accepted', 'declined') OR a.donor_message IS NOT NULL)
           ORDER BY a.id DESC''',
        (request_id,)
    ).fetchall()
    return jsonify([dict(m) for m in messages])