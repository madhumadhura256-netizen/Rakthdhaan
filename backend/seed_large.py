import sqlite3
import os
import random
import datetime

db_path = os.path.join(os.path.dirname(__file__), 'smart_blood.db')
schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Enable foreign keys
c.execute("PRAGMA foreign_keys = ON")

# Drop existing tables so the new schema (with new columns) is applied
for table in ['alerts_sent', 'donations', 'requests', 'blood_stock', 'donors', 'blood_banks', 'users']:
    c.execute(f"DROP TABLE IF EXISTS {table}")

# Recreate tables from schema.sql
with open(schema_path, 'r') as f:
    c.executescript(f.read())
conn.commit()

# Indian cities with coordinates and pincodes
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
    ("Nagpur", "440001", 21.1458, 79.0882),
    ("Indore", "452001", 22.7196, 75.8577),
    ("Bhopal", "462001", 23.2599, 77.4126),
    ("Visakhapatnam", "530001", 17.6868, 83.2185),
    ("Patna", "800001", 25.5941, 85.1376),
    ("Vadodara", "390001", 22.3072, 73.1812),
    ("Ludhiana", "141001", 30.9010, 75.8573),
    ("Agra", "282001", 27.1767, 78.0081),
    ("Nashik", "422001", 20.0000, 73.7800),
    ("Faridabad", "121001", 28.4089, 77.3178),
]

bank_names = [
    "City General Hospital Blood Bank", "Metro Blood Centre", "LifeLink Blood Bank",
    "Sunrise Blood Centre", "GreenCare Blood Bank", "Royal Blood Bank",
    "Apollo Blood Bank", "Fortis Blood Centre", "Max Blood Bank",
    "Manipal Blood Centre", "AIIMS Blood Bank", "PGIMER Blood Bank",
    "Safdarjung Blood Bank", "Lilavati Blood Centre", "Hinduja Blood Bank",
    "Ruby Hall Blood Centre", "Jehangir Blood Bank", "Bhatia Blood Bank",
    "Sahyadri Blood Centre", "Narayana Blood Bank", "Star Blood Centre",
    "Rainbow Blood Centre", "CARE Blood Bank", "AMRI Blood Bank",
    "Medica Blood Centre", "MGM Blood Bank", "Kokilaben Blood Bank",
    "Rajiv Gandhi Blood Centre", "Sanjay Gandhi Blood Centre", "Seth GS Blood Bank",
]

doctor_ids = [f"DOC{i:03d}" for i in range(1, 101)]

first_names = [
    "Rahul", "Priya", "Amit", "Sneha", "Vijay", "Ananya", "Rohan", "Meera",
    "Arjun", "Kavya", "Aditya", "Pooja", "Karan", "Divya", "Siddharth", "Neha",
    "Raj", "Shweta", "Manoj", "Ritu", "Sanjay", "Anjali", "Vivek", "Swati",
    "Ajay", "Komal", "Deepak", "Shruti", "Gaurav", "Nidhi", "Abhishek", "Preeti",
    "Nikhil", "Rashi", "Saurabh", "Monika", "Harsh", "Shivani", "Yash", "Tanuja",
    "Rishabh", "Sakshi", "Mohit", "Kriti", "Aryan", "Ishita", "Pratik", "Nikita",
    "Raghav", "Avni", "Krishna", "Sonia", "Ishaan", "Riya", "Vedant", "Aarohi",
    "Rajat", "Anushka", "Dev", "Kashish", "Omkar", "Smriti", "Samar", "Disha",
    "Atharv", "Pihu", "Aarav", "Anvi", "Vihaan", "Mira", "Reyansh", "Tara",
]
last_names = [
    "Sharma", "Patel", "Kumar", "Reddy", "Singh", "Das", "Nair", "Iyer",
    "Gupta", "Verma", "Jain", "Rao", "Shah", "Mehta", "Desai", "Kulkarni",
    "Joshi", "Pillai", "Menon", "Chopra", "Malhotra", "Agarwal", "Banerjee",
    "Chatterjee", "Mukherjee", "Ghosh", "Dasgupta", "Sen", "Bose", "Sengupta",
    "Choudhury", "Saxena", "Tiwari", "Pandey", "Mishra", "Dubey", "Jha",
    "Yadav", "Thakur", "Chauhan", "Rajput", "Sisodia", "Rathore", "Bhati",
]

blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
bg_weights = {'O+': 37, 'O-': 7, 'A+': 34, 'A-': 6, 'B+': 25, 'B-': 4, 'AB+': 4, 'AB-': 1}
bg_pool = []
for bg, weight in bg_weights.items():
    bg_pool.extend([bg] * weight)
random.shuffle(bg_pool)

genders = ['Male', 'Female', 'Other']
gender_weights = [50, 48, 2]

# --- Seed Blood Banks (with users first) ---
print("Seeding blood banks...")
bank_ids = []
for i in range(50):
    city, pincode, lat, lon = random.choice(cities)
    name = random.choice(bank_names)
    doc_id = random.choice(doctor_ids)

    email = f"bank{i+1}@example.com"
    c.execute(
        "INSERT INTO users (email, password_hash, role, phone, city) VALUES (?, ?, ?, ?, ?)",
        (email, "$2b$12$placeholderhash", "blood_bank", f"+91 {random.randint(7000000000, 9999999999)}", city)
    )
    user_id = c.lastrowid

    bank_id = c.execute(
        "INSERT INTO blood_banks (user_id, name, hospital_name, doctor_id, license_number, address, city, pincode, latitude, longitude, phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, name, name, doc_id, f"LIC{random.randint(100000,999999)}", f"{random.randint(1,999)} Main Road", city, pincode, lat, lon, f"+91 {random.randint(10000,99999)} {random.randint(10000,99999)}")
    ).lastrowid
    bank_ids.append(bank_id)

# --- Seed Blood Stock for each bank ---
print("Seeding blood stock...")
for bank_id in bank_ids:
    for bg in blood_groups:
        if bg in ('O-', 'AB-', 'B-', 'A-'):
            units = random.randint(0, 4)
        else:
            units = random.randint(0, 15)
        c.execute(
            "INSERT INTO blood_stock (blood_bank_id, blood_group, units_available) VALUES (?, ?, ?)",
            (bank_id, bg, units)
        )

# --- Seed Donors (with users first) ---
print("Seeding 500 donors...")
donor_ids = []
for i in range(500):
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    bg = random.choice(bg_pool)
    gender = random.choices(genders, weights=gender_weights, k=1)[0]
    age = random.randint(18, 65)
    city, pincode, lat, lon = random.choice(cities)
    lat += random.uniform(-0.05, 0.05)
    lon += random.uniform(-0.05, 0.05)
    phone = f"+91 {random.randint(7000000000, 9999999999)}"

    status = 'active'
    last_donation = None
    if random.random() < 0.15:
        status = 'inactive'
        last_donation = (datetime.date.today() - datetime.timedelta(days=random.randint(10, 60))).isoformat()

    is_rare = 1 if bg in ('O-', 'AB-', 'B-', 'A-') else 0

    aadhaar = f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}"
    mobile_verified = 1 if random.random() < 0.7 else 0
    sms_consent = 1 if random.random() < 0.6 else 0
    weight = random.randint(50, 90)
    previous_hb = round(random.uniform(11.0, 17.5), 1)
    diseases = random.choice(["None", "None", "None", "Diabetes", "Hypertension", "Asthma", "Anemia"])
    bad_habits = random.choice(["None", "None", "None", "Smoking", "Alcohol", "Smoking and alcohol"])
    disorders = random.choice(["None", "None", "None", "Bleeding disorder", "Allergies"])
    priority = 1 if random.random() < 0.1 else 0

    email = f"donor{i+1}@example.com"
    c.execute(
        "INSERT INTO users (email, password_hash, role, phone, city) VALUES (?, ?, ?, ?, ?)",
        (email, "$2b$12$placeholderhash", "donor", phone, city)
    )
    user_id = c.lastrowid

    donor_id = c.execute(
        """INSERT INTO donors
           (user_id, name, blood_group, gender, age, phone, aadhaar, mobile_verified,
            sms_consent, weight, previous_hb, diseases, bad_habits, disorders,
            pincode, latitude, longitude, city, last_donation_date, status, is_rare_group, priority)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, name, bg, gender, age, phone, aadhaar, mobile_verified,
         sms_consent, weight, previous_hb, diseases, bad_habits, disorders,
         pincode, lat, lon, city, last_donation, status, is_rare, priority)
    ).lastrowid
    donor_ids.append(donor_id)

# --- Seed Requests (30 requests) ---
print("Seeding requests...")
request_data = [
    ("Anita Sharma", "City General Hospital", "DOC001", "O+", 2, "critical", "Mumbai", "400001"),
    ("Raj Mehta", "Metro Blood Centre", "DOC002", "A+", 1, "urgent", "Delhi", "110001"),
    ("Priya Nair", "LifeLink Blood Bank", "DOC003", "B+", 3, "normal", "Bangalore", "560001"),
    ("Vikram Rao", "Sunrise Blood Centre", "DOC004", "AB+", 1, "urgent", "Chennai", "600001"),
    ("Sonia Kapoor", "GreenCare Blood Bank", "DOC005", "O-", 2, "critical", "Kolkata", "700001"),
    ("Amit Joshi", "Apollo Blood Bank", "DOC006", "A-", 1, "urgent", "Hyderabad", "500001"),
    ("Kavita Singh", "Fortis Blood Centre", "DOC007", "B+", 2, "normal", "Ahmedabad", "380001"),
    ("Ravi Kumar", "Max Blood Bank", "DOC008", "O+", 3, "critical", "Pune", "411001"),
    ("Neha Gupta", "Manipal Blood Centre", "DOC009", "AB-", 1, "urgent", "Jaipur", "302001"),
    ("Suresh Yadav", "AIIMS Blood Bank", "DOC010", "A+", 2, "normal", "Lucknow", "226001"),
    ("Divya Shah", "PGIMER Blood Bank", "DOC011", "B-", 1, "critical", "Nagpur", "440001"),
    ("Arjun Mehta", "Safdarjung Blood Bank", "DOC012", "O+", 2, "urgent", "Indore", "452001"),
    ("Pooja Nair", "Lilavati Blood Centre", "DOC013", "AB+", 1, "normal", "Bhopal", "462001"),
    ("Vivek Rao", "Hinduja Blood Bank", "DOC014", "A-", 2, "critical", "Visakhapatnam", "530001"),
    ("Ritu Desai", "Ruby Hall Blood Centre", "DOC015", "O+", 3, "urgent", "Patna", "800001"),
    ("Karan Chopra", "Jehangir Blood Bank", "DOC016", "B+", 1, "normal", "Vadodara", "390001"),
    ("Swati Agarwal", "Bhatia Blood Bank", "DOC017", "AB-", 1, "critical", "Ludhiana", "141001"),
    ("Sanjay Banerjee", "Sahyadri Blood Centre", "DOC018", "O-", 2, "urgent", "Agra", "282001"),
    ("Nidhi Joshi", "Narayana Blood Bank", "DOC019", "A+", 2, "normal", "Nashik", "422001"),
    ("Gaurav Das", "Star Blood Centre", "DOC020", "B+", 3, "critical", "Faridabad", "121001"),
    ("Mohan Lal", "CARE Blood Bank", "DOC021", "O+", 1, "urgent", "Mumbai", "400001"),
    ("Anita Verma", "AMRI Blood Bank", "DOC022", "AB+", 2, "normal", "Delhi", "110001"),
    ("Rohan Sen", "Medica Blood Centre", "DOC023", "A-", 1, "critical", "Bangalore", "560001"),
    ("Kavita Dasgupta", "MGM Blood Bank", "DOC024", "B+", 2, "urgent", "Chennai", "600001"),
    ("Vijay Ghosh", "Kokilaben Blood Bank", "DOC025", "O+", 3, "normal", "Kolkata", "700001"),
    ("Priya Bose", "Rajiv Gandhi Blood Centre", "DOC026", "AB-", 1, "critical", "Hyderabad", "500001"),
    ("Ajay Mukherjee", "Sanjay Gandhi Blood Centre", "DOC027", "A+", 2, "urgent", "Ahmedabad", "380001"),
    ("Shivani Sengupta", "Seth GS Blood Bank", "DOC028", "B-", 1, "normal", "Pune", "411001"),
    ("Yash Choudhury", "City General Hospital Blood Bank", "DOC029", "O+", 2, "critical", "Jaipur", "302001"),
    ("Tanuja Saxena", "Metro Blood Centre", "DOC030", "AB+", 1, "urgent", "Lucknow", "226001"),
]

for patient, hospital, doc_id, bg, units, priority, city, pincode in request_data:
    c.execute(
        "INSERT INTO requests (patient_name, hospital_name, doctor_id, blood_group, units_needed, priority, city, pincode, verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
        (patient, hospital, doc_id, bg, units, priority, city, pincode)
    )

conn.commit()
conn.close()
print("Data seeded successfully!")
print(f"Blood banks: 50")
print(f"Donors: 500")
print(f"Blood stock records: 400")
print(f"Requests: 30")