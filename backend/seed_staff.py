import os
import sqlite3

import bcrypt

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_blood.db')
PASSWORD = 'Demo@1234'

# email, role, doctor_id
ACCOUNTS = [
    ('doctor@raktdhan.test', 'doctor', 'DOC-1001'),
    ('paramedic@raktdhan.test', 'paramedical', None),
    ('bloodbank@raktdhan.test', 'blood_connect', None),
]

conn = sqlite3.connect(DB)
cols = {r[1] for r in conn.execute('PRAGMA table_info(users)')}
if 'doctor_id' not in cols:
    conn.execute('ALTER TABLE users ADD COLUMN doctor_id TEXT')
    cols.add('doctor_id')

pw = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
for email, role, doc_id in ACCOUNTS:
    row = conn.execute('SELECT id FROM users WHERE email = %s', (email,)).fetchone()
    if row:
        conn.execute('UPDATE users SET role=%s, password_hash=%s, verified=1, doctor_id=%s WHERE id=%s',
                     (role, pw, doc_id, row[0]))
    else:
        conn.execute(
            'INSERT INTO users (email, password_hash, role, verified, doctor_id) VALUES (%s,%s,%s,%s,%s)',
            (email, pw, role, 1, doc_id))
    print(f'{role:14} {email}  doctor_id={doc_id}')

conn.commit()
conn.close()
print('Password for all:', PASSWORD)