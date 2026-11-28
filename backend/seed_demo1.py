from app import app
from database import get_db
from hospital import _ensure_columns


def seed():
    with app.app_context():
        db = get_db()
        _ensure_columns(db)

        hospital = db.execute(
            "SELECT id, name, user_id FROM hospitals WHERE verified = 1 ORDER BY id LIMIT 1"
        ).fetchone()
        if not hospital:
            print("No verified hospital found. Verify one in the admin panel first.")
            return

        donors = db.execute(
            "SELECT id, name, blood_group, city FROM donors "
            "WHERE status = 'active' ORDER BY id LIMIT 3"
        ).fetchall()
        if len(donors) < 3:
            print("Need at least 3 active donors in the database.")
            return

        blood_group = donors[0]['blood_group']
        city = donors[0]['city'] or 'Bengaluru'

        cur = db.execute(
            '''INSERT INTO requests
               (patient_name, hospital_name, blood_group, units_needed,
                priority, status, verified, city)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            ('DEMO Patient (sample)', hospital['name'], blood_group, 2,
             'urgent', 'pending', 1, city)
        )
        request_id = cur.lastrowid

        db.execute(
            '''INSERT INTO request_bank_notices
               (request_id, blood_bank_id, status, distance_km)
               VALUES (%s, %s, 'notified', 3.4)''',
            (request_id, hospital['id'])
        )

        alerts = [
            (donors[0]['id'], 'accepted', 'I can reach the hospital by 6 PM today.'),
            (donors[1]['id'], 'declined', 'Sorry, I am unwell this week.'),
            (donors[2]['id'], 'sent', None),  # no response yet
        ]
        for donor_id, status, message in alerts:
            db.execute(
                '''INSERT INTO alerts_sent
                   (request_id, donor_id, status, donor_message)
                   VALUES (%s, %s, %s, %s)''',
                (request_id, donor_id, status, message)
            )

        db.commit()
        print(f"Demo request #{request_id} created for {hospital['name']}.")
        print("Log in as that hospital (or admin), open Hospital Inbox, and click View Donor Messages.")


if __name__ == '__main__':
    seed()