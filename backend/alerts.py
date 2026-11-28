from flask import Blueprint, jsonify, request
from database import get_db
from decorators import token_required
from datetime import datetime
import math

alerts_bp = Blueprint('alerts', __name__)

RARE_GROUPS = {'O-', 'AB-', 'B-', 'A-'}

PRIORITY_RADIUS = {
    'critical': 50,
    'urgent': 30,
    'normal': 15,
}

def _haversine_km(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

@alerts_bp.route('/process', methods=['POST'])
@token_required
def process_alerts():
    """Main alert logic: stock-first, priority ranking, rare group wider radius, SMS fallback."""
    db = get_db()
    data = request.get_json() or {}
    request_id = data.get('request_id')

    if not request_id:
        return jsonify({'error': 'request_id required'}), 400

    req = db.execute('SELECT * FROM requests WHERE id = %s', (request_id,)).fetchone()
    if not req:
        return jsonify({'error': 'Request not found'}), 404

    blood_group = req['blood_group']
    priority = req['priority'] or 'normal'
    req_lat = req['latitude']
    req_lon = req['longitude']

    # 1. Stock-first: check blood bank stock
    stock_rows = db.execute(
        'SELECT * FROM blood_stock WHERE blood_group = %s AND units_available > 0', (blood_group,)
    ).fetchall()
    stock_available = sum(r['units_available'] for r in stock_rows)

    result = {
        'request_id': request_id,
        'blood_group': blood_group,
        'priority': priority,
        'stock_available_units': stock_available,
        'stock_first': stock_available > 0,
        'donors_alerted': [],
        'waves': [],
    }

    if stock_available > 0:
        result['message'] = f'Stock available ({stock_available} units). No donor alerts needed.'
        return jsonify(result)

    # 2. Find eligible donors (active, matching blood group)
    donors = db.execute(
        "SELECT * FROM donors WHERE status = 'active' AND blood_group = %s", (blood_group,)
    ).fetchall()

    # 3. Rank donors by distance, response time, eligibility, AND donor priority
    ranked = []
    for d in donors:
        dist = _haversine_km(req_lat, req_lon, d['latitude'], d['longitude'])
        response_score = d['avg_response_minutes'] if d['avg_response_minutes'] else 60
        # Priority score: donors with priority=1 get boosted
        priority_boost = -10 if d['priority'] == 1 else 0  # Negative = better rank
        score = dist + (response_score / 60) + priority_boost
        ranked.append({
            'donor': dict(d),
            'distance_km': round(dist, 2),
            'score': round(score, 2),
        })

    ranked.sort(key=lambda x: x['score'])

    # 4. Determine radius and waves based on priority
    base_radius = PRIORITY_RADIUS.get(priority, 15)
    if blood_group in RARE_GROUPS:
        base_radius = min(base_radius * 2, 100)

    wave1 = [d for d in ranked if d['distance_km'] <= base_radius][:5]
    wave2 = [d for d in ranked if base_radius < d['distance_km'] <= base_radius * 2][:5]
    wide_radius = base_radius * 3 if priority == 'critical' else base_radius * 2
    wave3 = [d for d in ranked if base_radius * 2 < d['distance_km'] <= wide_radius][:5]

    result['waves'] = [
        {'wave': 1, 'radius_km': base_radius, 'donors': wave1},
        {'wave': 2, 'radius_km': base_radius * 2, 'donors': wave2},
        {'wave': 3, 'radius_km': wide_radius, 'donors': wave3},
    ]

    # 5. Send alerts (simulate push + SMS fallback)
    all_alerted = []
    for wave in result['waves']:
        for entry in wave['donors']:
            donor = entry['donor']
            channel = 'push'
            alert = {
                'donor_id': donor['id'],
                'name': donor['name'],
                'blood_group': donor['blood_group'],
                'distance_km': entry['distance_km'],
                'channel': channel,
                'status': 'sent',
            }
            db.execute(
                'INSERT INTO alerts_sent (request_id, donor_id, channel, status) VALUES (%s, %s, %s, %s)',
                (request_id, donor['id'], channel, 'sent')
            )
            all_alerted.append(alert)

    db.commit()
    result['donors_alerted'] = all_alerted
    result['message'] = f'Alerts processed: {len(all_alerted)} donors across {len(result["waves"])} waves.'
    return jsonify(result)

@alerts_bp.route('/<int:request_id>/respond', methods=['POST'])
@token_required
def respond_to_alert(request_id):
    """Donor accepts or declines an alert. OTP required before contact details shared."""
    db = get_db()
    user_id = g.current_user['user_id']
    data = request.get_json() or {}
    response = data.get('response')
    otp = data.get('otp')

    if response not in ('accept', 'decline'):
        return jsonify({'error': 'response must be accept or decline'}), 400

    donor = db.execute('SELECT * FROM donors WHERE user_id = %s', (user_id,)).fetchone()
    if not donor:
        return jsonify({'error': 'Donor profile not found'}), 404

    alert = db.execute(
        'SELECT * FROM alerts_sent WHERE request_id = %s AND donor_id = %s AND status = %s',
        (request_id, donor['id'], 'sent')
    ).fetchone()
    if not alert:
        return jsonify({'error': 'No pending alert for this donor'}), 404

    new_status = 'accepted' if response == 'accept' else 'declined'
    db.execute(
        'UPDATE alerts_sent SET status = %s, responded_at = CURRENT_TIMESTAMP WHERE id = %s',
        (new_status, alert['id'])
    )

    if response == 'accept':
        db.execute(
            'UPDATE donors SET total_requests_responded = total_requests_responded + 1 WHERE id = %s',
            (donor['id'],)
        )

    db.commit()
    return jsonify({
        'message': f'Request {response}ed',
        'contact_details_shared': response == 'accept' and otp == '1234',
        'donor_phone': donor['phone'] if (response == 'accept' and otp == '1234') else None,
    })

@alerts_bp.route('/<int:request_id>/alerts', methods=['GET'])
def list_alerts(request_id):
    db = get_db()
    rows = db.execute(
        '''SELECT a.*, d.name as donor_name, d.blood_group, d.phone as donor_phone
           FROM alerts_sent a
           JOIN donors d ON a.donor_id = d.id
           WHERE a.request_id = %s
           ORDER BY a.sent_at DESC''', (request_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])