from math import radians, sin, cos, asin, sqrt

from sms import send_sms

PRIORITY_RANK = {'critical': 0, 'urgent': 1, 'normal': 2}


def distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return 9999
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def sort_requests(requests_list):
    return sorted(requests_list, key=lambda r: PRIORITY_RANK.get(r['priority'], 2))


def rank_donors(req, donors):
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
            'SELECT donor_id FROM alerts_sent WHERE request_id = %s', (req['id'],)
        )
    }
    ranked = [d for d in rank_donors(req, donors) if d['id'] not in already][:limit]

    where = place or req['hospital_name']
    text = (
        f"{req['priority'].upper()}: {req['blood_group']} blood needed. "
        f"Please donate at {where}. Log in to Raktdhan to accept. - Raktdhan"
    )

    sent = 0
    for d in ranked:
        try:
            send_sms(d['phone'], text)
            status = 'sent'
            sent += 1
        except Exception as e:
            print('SMS failed for', d['phone'], e)
            status = 'failed'
        db.execute(
            "INSERT INTO alerts_sent (request_id, donor_id, channel, status) "
            "VALUES (%s, %s, 'sms', %s)",
            (req['id'], d['id'], status),
        )
    db.commit()
    return sent


def ensure_donor_columns(db):
    try:
        existing = {r[1] for r in db.execute('PRAGMA table_info(donors)').fetchall()}
    except Exception:
        return
    DONOR_COLUMNS = {
        'aadhaar': 'TEXT',
        'weight': 'REAL',
        'previous_hb': 'REAL',
        'diseases': "TEXT DEFAULT 'None'",
        'bad_habits': "TEXT DEFAULT 'None'",
        'disorders': "TEXT DEFAULT 'None'",
        'sms_consent': 'INTEGER DEFAULT 0',
    }
    for col, decl in DONOR_COLUMNS.items():
        if col not in existing:
            try:
                db.execute(f'ALTER TABLE donors ADD COLUMN {col} {decl}')
            except Exception:
                pass
    db.commit()


def ensure_donation_history_columns(db):
    try:
        existing = {row['name'] for row in db.execute('PRAGMA table_info(donors)')}
    except Exception:
        return
    if 'has_donated_before' not in existing:
        try:
            db.execute("ALTER TABLE donors ADD COLUMN has_donated_before INTEGER DEFAULT 0")
            db.execute("UPDATE donors SET has_donated_before = 1 WHERE last_donation_date IS NOT NULL")
        except Exception:
            pass
    if 'next_eligible_date' not in existing:
        try:
            db.execute("ALTER TABLE donors ADD COLUMN next_eligible_date TEXT")
        except Exception:
            pass
    db.commit()


def refresh_donor_status(db):
    try:
        db.execute(
            "UPDATE donors SET status = 'active' "
            "WHERE status = 'inactive' AND next_eligible_date IS NOT NULL "
            "AND next_eligible_date <= CURRENT_DATE"
        )
        db.commit()
    except Exception:
        pass


def ensure_request_columns(db):
    try:
        existing = {r[1] for r in db.execute('PRAGMA table_info(requests)').fetchall()}
    except Exception:
        existing = set()
    if 'nurse_id' not in existing:
        try:
            db.execute("ALTER TABLE requests ADD COLUMN nurse_id TEXT")
        except Exception:
            pass
    if 'paramedic_id' not in existing:
        try:
            db.execute("ALTER TABLE requests ADD COLUMN paramedic_id TEXT")
        except Exception:
            pass
    db.commit()


def ensure_request_flow_tables(db):
    db.execute('''
        CREATE TABLE IF NOT EXISTS request_bank_notices (
            id SERIAL PRIMARY KEY,
            request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
            blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id) ON DELETE CASCADE,
            distance_km REAL,
            status TEXT DEFAULT 'notified' CHECK (status IN ('notified', 'accepted', 'declined', 'fulfilled')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            responded_at TEXT,
            UNIQUE (request_id, blood_bank_id)
        )
    ''')
    db.execute(
        'CREATE INDEX IF NOT EXISTS idx_notices_bank ON request_bank_notices(blood_bank_id)'
    )
    db.commit()