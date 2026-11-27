import random
import requests

API = "https://rakthdhaan.onrender.com"

CITIES = ["Bengaluru", "Mumbai", "Delhi", "Chennai", "Hyderabad"]
GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
NAMES = ["Arjun Rao", "Priya Nair", "Rahul Verma", "Sneha Iyer", "Vikram Singh",
         "Meera Patel", "Karan Mehta", "Ananya Das", "Rohit Kumar", "Divya Menon"]

for i, name in enumerate(NAMES):
    body = {
        "name": name,
        "email": f"demo{i}_{random.randint(1000, 9999)}@example.com",
        "password": "demo1234",
        "phone": f"9{random.randint(100000000, 999999999)}",
        "age": random.randint(20, 50),
        "gender": random.choice(["Male", "Female"]),
        "blood_group": random.choice(GROUPS),
        "city": random.choice(CITIES),
        "weight": 70,
        "previous_hb": 14.0,
        "diseases": "None",
        "bad_habits": "None",
        "disorders": "None",
        "sms_consent": 1,
        "has_donated_before": 0,
        "status": "active",
        "role": "donor",
    }
    r = requests.post(f"{API}/api/auth/register", json=body, timeout=60)
    print(name, r.status_code, r.text[:120])