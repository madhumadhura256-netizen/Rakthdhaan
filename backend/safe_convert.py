import os

backend_dir = os.path.dirname(os.path.abspath(__file__))

# Only these route files need %s -> %s conversion.
# database.py and Migrations.py already converted or excluded.
files_to_convert = [
    "auth.py",
    "donors.py",
    "requests_api.py",
    "bloodbank.py",
    "alerts.py",
    "transfers.py",
    "hospital.py",
    "otp.py",
    "check_requests.py",
    "routing.py",
    "make_admin.py",
    "reset_password.py",
    "seed_bank.py",
    "seed_demo.py",
    "seed_demo1.py",
    "seed_hospital_data.py",
    "seed_inbox.py",
    "seed_large.py",
    "seed_staff.py",
    "Create_staff.py",
    "matching.py",
]

for name in files_to_convert:
    path = os.path.join(backend_dir, name)
    if not os.path.exists(path):
        print(f"SKIP (not found): {name}")
        continue
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    new_content = content.replace("%s", "%s")
    if new_content != content:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        print(f"CONVERTED: {name}")
    else:
        print(f"UNCHANGED: {name}")

print("Done.")
