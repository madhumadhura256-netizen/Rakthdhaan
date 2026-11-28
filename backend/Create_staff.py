"""Create a staff login (public signup only allows donor/requester).

Usage:
    python create_staff.py doctor@test.com Pass123 doctor
Roles: admin, doctor, paramedical, blood_connect
"""
import sys
from app import app
from auth import bcrypt
from database import get_db

STAFF = {'admin', 'doctor', 'paramedical', 'blood_connect'}


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return
    email, password, role = sys.argv[1:4]
    if role not in STAFF:
        print(f'Role must be one of: {", ".join(sorted(STAFF))}')
        return
    with app.app_context():
        db = get_db()
        if db.execute('SELECT id FROM users WHERE email = %s', (email,)).fetchone():
            print('That email already exists.')
            return
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        db.execute(
            'INSERT INTO users (email, password_hash, role, phone, city) VALUES (%s, %s, %s, %s, %s)',
            (email, pw_hash, role, '', ''),
        )
        db.commit()
        print(f'Created {role} account: {email}')


if __name__ == '__main__':
    main()