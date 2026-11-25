from math import radians, sin, cos, asin, sqrt

from sms import send_sms

PRIORITY_RANK = {'critical': 0, 'urgent': 1, 'normal': 2}


def distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return 9999  # unknown location goes last
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def sort_requests(requests_list):
    """Level 1: critical patients first."""
    return sorted(requests_list, key=lambda r: PRIORITY_RANK.get(r['priority'], 2))


def rank_donors(req, donors):
    """Level 2: active + same blood group, previous donors first, then nearest."""
    eligible = [
        d for d in donors
        if d['status'] == 'active'
        and d['blood_group'] == req['blood_group']
        and d['sms_consent']
    ]
    return sorted(
        eligible,
        key=lambda d: (
            0 if d['has_donated_before'] else 1,
            distance_km(req['latitude'], req['longitude'], d['latitude'], d['longitude']),
        ),
    )


def alert_donors(db, req, donors, limit=20, place=None):
    already = {
        row['donor_id']
        for row in db.execute(
            'SELECT donor_id FROM alerts_sent WHERE request_id = ?', (req['id'],)
        )
    }
    ranked = [d for d in rank_donors(req, donors) if d['id'] not in already][:limit]

    where = place or req['hospital_name']
    text = (
        f"{req['priority'].upper()}: {req['blood_group']} blood needed. "
        f"Please donate at {where}. Log in to Raktdhan to accept. - Raktdhan"
    )

    sent = 0
    for d in ranked:  # previous donors are texted first
        try:
            send_sms(d['phone'], text)
            status = 'sent'
            sent += 1
        except Exception as e:
            print('SMS failed for', d['phone'], e)
            status = 'failed'
        db.execute(
            "INSERT INTO alerts_sent (request_id, donor_id, channel, status) "
            "VALUES (?, ?, 'sms', ?)",
            (req['id'], d['id'], status),
        )
    db.commit()
    return sent