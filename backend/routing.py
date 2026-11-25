from matching import distance_km

MAX_BANKS = 5      # how many banks get each request
MAX_KM = 50        # preferred search radius


def nearest_banks(db, req, limit=MAX_BANKS, max_km=MAX_KM):
    banks = [dict(b) for b in db.execute('SELECT * FROM blood_banks').fetchall()]
    lat, lon = req.get('latitude'), req.get('longitude')
    near = []

    # 1) Use coordinates when we have them
    if lat is not None and lon is not None:
        for b in banks:
            b['distance_km'] = distance_km(lat, lon, b.get('latitude'), b.get('longitude'))
        known = sorted(
            (b for b in banks if b['distance_km'] < 9999),
            key=lambda b: b['distance_km'],
        )
        # nothing inside the radius? still use the 3 closest
        near = [b for b in known if b['distance_km'] <= max_km] or known[:3]

    # 2) Otherwise fall back to banks in the same city
    if not near:
        city = (req.get('city') or '').strip().lower()
        near = [b for b in banks if city and (b.get('city') or '').strip().lower() == city]
        for b in near:
            b['distance_km'] = None

    return near[:limit]


def notify_banks(db, req):
    """Put the request in every nearby bank's inbox. Safe to call twice."""
    banks = nearest_banks(db, req)
    for b in banks:
        db.execute(
            'INSERT OR IGNORE INTO request_bank_notices (request_id, blood_bank_id, distance_km) '
            'VALUES (?, ?, ?)',
            (req['id'], b['id'], b['distance_km']),
        )
    db.commit()
    return banks


def stock_summary(db, req):
    """Live stock of the requested blood group at each bank that got the request."""
    rows = db.execute('''
        SELECT n.blood_bank_id, n.distance_km, b.name, b.city,
               COALESCE(s.units_available, 0) AS units
        FROM request_bank_notices n
        JOIN blood_banks b ON b.id = n.blood_bank_id
        LEFT JOIN blood_stock s
               ON s.blood_bank_id = n.blood_bank_id AND s.blood_group = ?
        WHERE n.request_id = ?
        ORDER BY n.distance_km IS NULL, n.distance_km
    ''', (req['blood_group'], req['id'])).fetchall()

    needed = req.get('units_needed') or 1
    return [{**dict(r), 'enough': r['units'] >= needed} for r in rows]


def routing_message(req, summary):
    bg = req['blood_group']
    if not summary:
        return (f"Request created. No blood bank was found near this location. "
                f"Donors with {bg} will be alerted after verification.")

    in_stock = [s for s in summary if s['enough']]
    if in_stock:
        return (f"Request created and sent to {len(summary)} nearby blood bank(s). "
                f"{in_stock[0]['name']} has {bg} in stock.")

    return (f"Request created and sent to {len(summary)} nearby blood bank(s). "
            f"None has enough {bg}, so matching donors will be alerted after verification.")