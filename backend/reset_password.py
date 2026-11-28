import os
import re
import sqlite3
import getpass

import bcrypt

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_blood.db')

email = input('Account email: ').strip().lower()
password = getpass.getpass('New password (8+ chars, letter and number): ')
if len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
    raise SystemExit('Password too weak. Nothing changed.')
if password != getpass.getpass('Confirm password: '):
    raise SystemExit('Passwords do not match. Nothing changed.')

pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
conn = sqlite3.connect(DB)
cur = conn.execute('UPDATE users SET password_hash = %s WHERE lower(email) = %s', (pw_hash, email))
conn.commit()
print('Password updated.' if cur.rowcount else 'No account with that email.')
conn.close()