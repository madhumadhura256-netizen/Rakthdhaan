import os
import sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_blood.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print('Existing blood banks:')
for b in conn.execute('SELECT id, name, city FROM blood_banks'):
    print(f"  ID {b['id']}: {b['name']} ({b['city']})")

print('\nExisting donors:')
for d in conn.execute('SELECT id, name, blood_group, status FROM donors'):
    print(f"  ID {d['id']}: {d['name']} {d['blood_group']} [{d['status']}]")

if input('\nCreate a new blood bank%s (y/n): ').strip().lower() == 'y':
    email = input('Admin email that owns it: ').strip().lower()
    user = conn.execute('SELECT id FROM users WHERE lower(email) = %s', (email,)).fetchone()
    if not user:
        raise SystemExit('No user with that email.')
    name = input('Blood bank name: ').strip() or 'City Blood Bank'
    city = input('City: ').strip() or 'Bengaluru'
    phone = input('Phone: ').strip()
    cur = conn.execute(
        'INSERT INTO blood_banks (user_id, name, city, phone) VALUES (%s, %s, %s, %s)',
        (user['id'], name, city, phone),
    )
    conn.commit()
    print('Created. Blood bank ID =', cur.lastrowid)

conn.close()