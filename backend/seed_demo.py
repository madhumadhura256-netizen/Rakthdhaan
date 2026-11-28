"""Demo data for hospital verification + hospital inbox. Safe to re-run."""
import os
import sqlite3
from datetime import datetime, timedelta

import bcrypt

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_blood.db')
PASSWORD = 'Demo@1234'
REACTIVATE_DONORS = True   # demo only: clears cooldown so donations can be recorded again

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
skipped = set()
now = lambda d=0: (datetime.now() - timedelta(days=d)).isoformat(' ', 'seconds')


def insert(table, **values):
    """Insert only columns that exist in your schema (reports the ones it skipped)."""
    cols = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}
    skipped.update(f'{table}.{k}' for k in values if k not in cols)
    values = {k: v for k, v in values.items() if k in cols}
    cur = conn.execute(
        f'INSERT INTO {table} ({", ".join(values)}) VALUES ({", ".join("%s" * len(values))})',
        list(values.values()),
    )
    return cur.lastrowid


def next_hospital_id():
    row = conn.execute('SELECT hospital_id FROM hospitals ORDER BY id DESC LIMIT 1').fetchone()
    try:
        n = int(row['hospital_id'].split('-')[1]) + 1
    except (TypeError, IndexError, ValueError):
        n = 1
    return f'HOSP-{n:04d}'


pw_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

# name, city, lat, lon, already verified%s
HOSPITALS = [
    ('City Care Hospital', 'Bengaluru', 12.9716, 77.5946, 1),
    ('Lakeview Medical Centre', 'Bengaluru', 12.9352, 77.6245, 0),
    ('Sunrise Multispeciality Hospital', 'Bengaluru', 13.0358, 77.5970, 0),
    ('Greenfield General Hospital', 'Mysuru', 12.2958, 76.6394, 0),
]
STOCK = {'A+': 12, 'A-': 3, 'B+': 9, 'B-': 0, 'AB+': 4, 'AB-': 1, 'O+': 15, 'O-': 2}
REQUESTS = [  # patient, blood group, units, priority, verified
    ('Anita Rao', 'A+', 2, 'critical', 1),
    ('Mohammed Iqbal', 'O-', 1, 'critical', 1),
    ('Kavya Nair', 'B+', 3, 'urgent', 1),
    ('Suresh Kumar', 'AB-', 2, 'urgent', 0),
    ('Priya Menon', 'O+', 1, 'normal', 1),
]

# A requester account to own the demo requests
req_email = 'demo.requester@raktdhan.test'
row = conn.execute('SELECT id FROM users WHERE email = %s', (req_email,)).fetchone()
requester_id = row['id'] if row else insert(
    'users', email=req_email, password_hash=pw_hash, role='requester', phone='', city='Bengaluru', verified=1)

for i, (name, city, lat, lon, verified) in enumerate(HOSPITALS, start=1):
    email = f'demo.hospital{i}@raktdhan.test'
    if conn.execute('SELECT id FROM users WHERE email = %s', (email,)).fetchone():
        print(f'skip (exists): {name}')
        continue

    phone = f'98450000{i:02d}'
    user_id = insert('users', email=email, password_hash=pw_hash, role='hospital',
                     phone=phone, city=city, verified=verified)
    hid = insert(
        'hospitals', user_id=user_id, hospital_id=next_hospital_id(), name=name,
        address=f'{i * 12}, Main Road, {city}', city=city, pincode='560001',
        latitude=lat, longitude=lon, phone=phone, email=email,
        license_number=f'KA-HOSP-{2000 + i}', license_document=None,
        verified=verified, verified_at=now() if verified else None,
        verification_notes='Demo data' if verified else None, created_at=now(i),
    )
    print(f'added: {name} ({"verified" if verified else "pending"})  login: {email}')

    if not verified:
        continue

    for bg, units in STOCK.items():
        insert('hospital_blood_stock', hospital_id=hid, blood_group=bg,
               units_available=units, last_updated=now())

    insert('hospital_sms_log', hospital_id=hid, blood_group='O+', donors_count=14, sent_by=user_id,
           message=f'URGENT: {name} needs O+ blood donors. Please contact {phone} to donate. - Raktdhan',
           status='sent', sent_at=now(2))
    insert('hospital_sms_log', hospital_id=hid, blood_group='A+', donors_count=9, sent_by=user_id,
           message=f'URGENT: {name} needs A+ blood donors. Please contact {phone} to donate. - Raktdhan',
           status='partial', sent_at=now(1))

    for patient, bg, units, prio, ver in REQUESTS:
        insert('requests', patient_name=patient, hospital_name=name, doctor_id='DOC-1001',
               blood_group=bg, units_needed=units, priority=prio, city=city,
               latitude=lat, longitude=lon, status='pending', verified=ver,
               user_id=requester_id, requester_id=requester_id, created_at=now())

if REACTIVATE_DONORS:
    conn.execute("UPDATE donors SET status = 'active', last_donation_date = NULL, next_eligible_date = NULL")
    print('All donors set to active (demo).')

conn.commit()
conn.close()
print(f'\nDemo hospital logins use password: {PASSWORD}')
if skipped:
    print('Columns not in your schema (skipped):', ', '.join(sorted(skipped)))