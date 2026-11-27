import requests

API = "https://rakthdhaan.onrender.com"

DONORS = [
    ("Arjun Rao", "Bengaluru", "A+", "Male"),
    ("Priya Nair", "Bengaluru", "B+", "Female"),
    ("Rahul Verma", "Mumbai", "O+", "Male"),
    ("Sneha Iyer", "Chennai", "AB+", "Female"),
    ("Vikram Singh", "Delhi", "O-", "Male"),
]

for i, (name, city, group, gender) in enumerate(DONORS, start=1):
    email = f"demo{i}@raktdhan.test"
    body = {
        "name": name,
        "email": email,
        "password": "demo1234",
        "phone": f"900000000{i}",
        "age": 28,
        "gender": gender,
        "blood_group": group,
        "city": city,
        "weight": 70,
        "previous_hb": 14.0,
        "diseases": "None",
        "bad_habits": "None",
        "disorders": "None",
        "sms_consent": 0,
        "has_donated_before": 0,
        "status": "active",
        "role": "donor",
    }
    r = requests.post(f"{API}/api/auth/register", json=body, timeout=60)
    print(f"{r.status_code}  {email}  password: demo1234  ({r.text[:60]})")