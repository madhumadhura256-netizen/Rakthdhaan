import json
import os
import sqlite3
from urllib.parse import quote

DB_PATH = os.path.join(os.path.dirname(__file__), "smart_blood.db")  # change if your DB is elsewhere


def doc(name, label):
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='420' height='260'>"
        "<rect width='100%' height='100%' fill='#f5f5f5'/>"
        f"<text x='20' y='60' font-size='24'>{label}</text>"
        "<text x='20' y='100' font-size='14'>Dummy document for demo</text></svg>"
    )
    return {"name": name, "data": "data:image/svg+xml;utf8," + quote(svg)}


ROWS = [
    ("Ravi Kumar", "Manipal Hospital", "DOC-1021", "O-", 3, "critical", "Bengaluru",
     "Road accident patient in ICU, needs O- blood urgently for surgery.",
     [doc("Doctor prescription", "Prescription - Dr. Mehta"), doc("Patient ID", "Patient ID card")],
     "City Blood Bank", 2.4, 1),
    ("Sunita Rao", "Apollo Hospital", "DOC-2045", "B+", 2, "urgent", "Bengaluru",
     "Scheduled surgery tomorrow morning, 2 units of B+ required.",
     [doc("Doctor prescription", "Prescription - Dr. Iyer")],
     "Red Cross Blood Bank", 5.1, 4),
    ("Arjun Nair", "Fortis Hospital", "DOC-3310", "A+", 1, "normal", "Bengaluru",
     "Thalassemia patient, regular transfusion.",
     [doc("Medical report", "Medical report")],
     "City Blood Bank", 7.8, 6),
    ("Meena Das", "Narayana Health", "DOC-4102", "AB-", 2, "critical", "Bengaluru",
     "Delivery complication, rare group needed immediately.",
     [doc("Doctor prescription", "Prescription - Dr. Shetty"), doc("Admission slip", "Admission slip")],
     "Red Cross Blood Bank", 3.3, 0),
]

con = sqlite3.connect(DB_PATH)
con.execute('''CREATE TABLE IF NOT EXISTS request_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT, hospital_name TEXT, doctor_id TEXT,
    blood_group TEXT, units_needed INTEGER DEFAULT 1,
    priority TEXT DEFAULT 'normal', city TEXT,
    message TEXT, documents TEXT DEFAULT '[]',
    requester_phone TEXT, bank_name TEXT,
    distance_km REAL, units_in_stock INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0, verified_by INTEGER,
    verified_at TIMESTAMP, otp_code TEXT,
    notice_status TEXT DEFAULT 'notified',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

con.execute("DELETE FROM request_inbox")   # running again resets the demo rows

for r in ROWS:
    con.execute(
        '''INSERT INTO request_inbox
           (patient_name, hospital_name, doctor_id, blood_group, units_needed, priority, city,
            message, documents, requester_phone, bank_name, distance_km, units_in_stock)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s)''',
        (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], json.dumps(r[8]), r[9], r[10], r[11]),
    )

con.commit()
con.close()
print("Added", len(ROWS), "dummy requests (IDs 1 to", len(ROWS), ")")