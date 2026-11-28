import os
import re
import sqlite3
import getpass

import bcrypt

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_blood.db')

email = input('Admin email: ').strip().lower()

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

user = conn.execute('SELECT id, role FROM users WHERE email = %s', (email,)).fetchone()

if user:
    # Email already registered: just promote it
    conn.execute("UPDATE users SET role = 'admin', verified = 1 WHERE id = %s", (user['id'],))
    conn.commit()
    print(f"Done. {email} was '{user['role']}' and is now admin.")
else:
    # No account yet: create a new admin
    password = getpass.getpass('Password (8+ chars, letter and number): ')
    if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        raise SystemExit('Password too weak. Nothing was created.')
    if password != getpass.getpass('Confirm password: '):
        raise SystemExit('Passwords do not match. Nothing was created.')

    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn.execute(
        "INSERT INTO users (email, password_hash, role, verified) VALUES (%s, %s, 'admin', 1)",
        (email, pw_hash),
    )
    conn.commit()
    print(f'Done. New admin created: {email}')

conn.close()