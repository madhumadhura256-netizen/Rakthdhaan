import sys
sys.path.insert(0, 'C:/Users/Varshini P/OneDrive/Desktop/raktdhan/backend')

from flask import Flask
from flask_bcrypt import Bcrypt
from database import init_db, get_db
import random
from datetime import date, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-me'
app.config['DATABASE'] = 'smart_blood.db'
bcrypt = Bcrypt(app)

with app.app_context():
    db = get_db()

    # Clear existing data
    print("Clearing existing data...")
    tables = ['alerts_sent', 'donations', 'request_bank_notices', 'requests',
              'hospital_blood_stock', 'hospital_sms_log', 'hospitals', 'users']
    for t in tables:
        db.execute(f'DELETE FROM {t}')
        db.execute(f'DELETE FROM sqlite_sequence WHERE name = %s', (t,))
    db.commit()

    # Indian cities with coordinates
    cities = [
        ("Mumbai", "400001", 19.0760, 72.8777),
        ("Delhi", "110001", 28.6139, 77.2090),
        ("Bangalore", "560001", 12.9716, 77.5946),
        ("Chennai", "600001", 13.0827, 80.2707),
        ("Kolkata", "700001", 22.5726, 88.3639),
        ("Hyderabad", "500001", 17.3850, 78.4867),
        ("Ahmedabad", "380001", 23.0225, 72.5714),
        ("Pune", "411001", 18.5204, 73.8567),
        ("Jaipur", "302001", 26.9124, 75.7873),
        ("Lucknow", "226001", 26.8467, 80.9462),
    ]

    hospital_names = [
        "City General Hospital", "Metro Heart Institute", "LifeCare Medical Center",
        "Sunrise Multi-specialty Hospital", "Green Valley Hospital", "Royal Medical Center",
        "Apollo Hospital", "Fortis Hospital", "Max Super Speciality Hospital",
        "Manipal Hospital", "AIIMS", "PGIMER", "Safdarjung Hospital",
        "Lilavati Hospital", "Hinduja Hospital", "Ruby Hall Clinic",
        "Jehangir Hospital", "Bhatia Hospital", "Sahyadri Hospital", "Narayana Health",
    ]

    doctor_ids = [f"DOC{i:03d}" for i in range(1, 51)]
    nurse_ids = [f"NUR{i:03d}" for i in range(1, 51)]
    paramedic_ids = [f"PAR{i:03d}" for i in range(1, 51)]

    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

    # Create hospital users and profiles
    print("Creating hospital users and profiles...")
    for i in range(15):
        city, pincode, lat, lon = random.choice(cities)
        name = random.choice(hospital_names)
        doctor_id = random.choice(doctor_ids)
        nurse_id = random.choice(nurse_ids)
        paramedic_id = random.choice(paramedic_ids)

        email = f"hospital{i+1}@example.com"
        phone = f"+91 {random.randint(7000000000, 9999999999)}"
        license_num = f"HLIC{random.randint(100000,999999)}"

        # Create user with hospital role
        pw_hash = bcrypt.generate_password_hash("hospital123").decode('utf-8')
        cursor = db.execute(
            'INSERT INTO users (email, password_hash, role, phone, city, verified, verified_at) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (email, pw_hash, 'hospital', phone, city, 1, date.today().isoformat())
        )
        user_id = cursor.lastrowid

        # Create hospital profile
        hospital_id = f"HOSP-{i+1:04d}"
        cursor = db.execute(
            '''INSERT INTO hospitals (user_id, hospital_id, name, address, city, pincode,
                   latitude, longitude, phone, email, license_number, verified, verified_by, verified_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (user_id, hospital_id, name, f"{random.randint(1,999)} Main Road", city, pincode,
             lat + random.uniform(-0.02, 0.02), lon + random.uniform(-0.02, 0.02),
             phone, email, license_num, 1, 1, date.today().isoformat())
        )
        hospital_db_id = cursor.lastrowid

        # Add hospital blood stock
        for bg in blood_groups:
            units = random.randint(0, 20) if bg in ('O+', 'A+', 'B+') else random.randint(0, 10)
            db.execute(
                'INSERT INTO hospital_blood_stock (hospital_id, blood_group, units_available) VALUES (%s, %s, %s)',
                (hospital_db_id, bg, units)
            )

    # Create paramedical/nurse staff users
    print("Creating paramedical staff...")
    for i in range(10):
        city, pincode, lat, lon = random.choice(cities)
        role = random.choice(['paramedical', 'nurse'])
        staff_id = f"PAR{100+i:03d}" if role == 'paramedical' else f"NUR{100+i:03d}"
        email = f"{role}{i+1}@example.com"
        phone = f"+91 {random.randint(7000000000, 9999999999)}"

        pw_hash = bcrypt.generate_password_hash("staff123").decode('utf-8')
        db.execute(
            'INSERT INTO users (email, password_hash, role, phone, city, verified, verified_at) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (email, pw_hash, role, phone, city, 1, date.today().isoformat())
        )

    # Create blood bank staff users
    print("Creating blood bank staff...")
    for i in range(5):
        city, pincode, lat, lon = random.choice(cities)
        email = f"bloodbank_staff{i+1}@example.com"
        phone = f"+91 {random.randint(7000000000, 9999999999)}"

        pw_hash = bcrypt.generate_password_hash("bloodbank123").decode('utf-8')
        db.execute(
            'INSERT INTO users (email, password_hash, role, phone, city, verified, verified_at) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (email, pw_hash, 'blood_connect', phone, city, 1, date.today().isoformat())
        )

    # Create some blood requests with doctor info
    print("Creating blood requests with doctor details...")
    requests_data = [
        ("Anita Sharma", "City General Hospital", "DOC001", "NUR001", "PAR001", "O+", 2, "critical", "Mumbai", "400001"),
        ("Raj Mehta", "Metro Heart Institute", "DOC002", "NUR002", "PAR002", "A+", 1, "urgent", "Delhi", "110001"),
        ("Priya Nair", "LifeCare Medical Center", "DOC003", "NUR003", "PAR003", "B+", 3, "normal", "Bangalore", "560001"),
        ("Vikram Rao", "Sunrise Hospital", "DOC004", "NUR004", "PAR004", "AB+", 1, "urgent", "Chennai", "600001"),
        ("Sonia Kapoor", "Green Valley Hospital", "DOC005", "NUR005", "PAR005", "O-", 2, "critical", "Kolkata", "700001"),
        ("Amit Joshi", "Royal Medical Center", "DOC006", "NUR006", "PAR006", "A-", 1, "urgent", "Hyderabad", "500001"),
        ("Kavita Singh", "Apollo Hospital", "DOC007", "NUR007", "PAR007", "B+", 2, "normal", "Ahmedabad", "380001"),
        ("Ravi Kumar", "Fortis Hospital", "DOC008", "NUR008", "PAR008", "O+", 3, "critical", "Pune", "411001"),
        ("Neha Gupta", "Max Hospital", "DOC009", "NUR009", "PAR009", "AB-", 1, "urgent", "Jaipur", "302001"),
        ("Suresh Yadav", "Manipal Hospital", "DOC010", "NUR010", "PAR010", "A+", 2, "normal", "Lucknow", "226001"),
    ]

    # Create verified requests (first 5)
    verified_requests = requests_data[:5]
    for patient, hospital_name, doc_id, nurse_id, para_id, bg, units, priority, city, pincode in verified_requests:
        db.execute(
            '''INSERT INTO requests (patient_name, hospital_name, doctor_id, nurse_id, paramedic_id,
                   blood_group, units_needed, priority, city, pincode, verified, verified_by, verified_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (patient, hospital_name, doc_id, nurse_id, para_id, bg, units, priority, city, pincode, 1, 1, date.today().isoformat())
        )

    # Create unverified requests (last 5) - for admin to verify
    unverified_requests = requests_data[5:]
    for patient, hospital_name, doc_id, nurse_id, para_id, bg, units, priority, city, pincode in unverified_requests:
        db.execute(
            '''INSERT INTO requests (patient_name, hospital_name, doctor_id, nurse_id, paramedic_id,
                   blood_group, units_needed, priority, city, pincode, verified)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (patient, hospital_name, doc_id, nurse_id, para_id, bg, units, priority, city, pincode, 0)
        )

    # Create hospital inbox notices for verified requests
    print("Creating hospital inbox notices...")
    hospitals = db.execute('SELECT id, name, latitude, longitude FROM hospitals WHERE verified = 1').fetchall()
    requests = db.execute('SELECT id, blood_group, hospital_name FROM requests WHERE verified = 1').fetchall()

    for req in requests:
        # Find nearest hospital
        for hosp in hospitals:
            db.execute(
                '''INSERT INTO request_bank_notices (request_id, blood_bank_id, status, distance_km)
                   VALUES (%s, %s, %s, %s)''',
                (req['id'], hosp['id'], 'notified', round(random.uniform(1, 15), 1))
            )
            break  # Just assign to first hospital for demo

    # Create some alerts_sent for donor responses
    print("Creating donor alerts...")
    donors = db.execute('SELECT id, blood_group FROM donors WHERE status = "active" AND sms_consent = 1').fetchall()
    for req in requests:
        matching_donors = [d for d in donors if d['blood_group'] == req['blood_group']][:5]
        for donor in matching_donors:
            status = random.choice(['sent', 'delivered', 'accepted', 'declined'])
            db.execute(
                '''INSERT INTO alerts_sent (request_id, donor_id, channel, status, sent_at, responded_at)
                   VALUES (%s, %s, %s, %s, %s, %s)''',
                (req['id'], donor['id'], 'sms', status,
                 (date.today() - timedelta(days=random.randint(0, 5))).isoformat(),
                 (date.today() - timedelta(days=random.randint(0, 3))).isoformat() if status in ('accepted', 'declined') else None)
            )

    # Create SMS history for hospitals
    print("Creating SMS history...")
    for hosp in hospitals[:5]:
        for _ in range(random.randint(1, 3)):
            bg = random.choice(blood_groups)
            db.execute(
                '''INSERT INTO hospital_sms_log (hospital_id, blood_group, donors_count, message, sent_by, status)
                   VALUES (%s, %s, %s, %s, %s, %s)''',
                (hosp['id'], bg, random.randint(5, 30),
                 f"URGENT: {hosp['name']} needs {bg} blood donors.",
                 1, random.choice(['sent', 'partial']))
            )

    db.commit()
    print("Done! Created:")
    print(f"  - 15 verified hospitals with stock")
    print(f"  - 10 paramedical/nurse staff")
    print(f"  - 5 blood bank staff")
    print(f"  - 5 verified blood requests + 5 unverified (for admin verification)")
    print(f"  - Hospital inbox notices for verified requests")
    print(f"  - Donor alerts")
    print(f"  - SMS history")