import os
import sqlite3

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_blood.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print('ID | patient | blood | priority | verified')
for r in conn.execute(
    'SELECT id, patient_name, blood_group, priority, verified FROM requests ORDER BY id'
):
    mark = 'yes' if r['verified'] else 'NO (can verify)'
    print(f"{r['id']:>2} | {r['patient_name']} | {r['blood_group']} | {r['priority']} | {mark}")

rid = input('\nRequest ID to reset to unverified for testing (Enter to skip): ').strip()
if rid.isdigit():
    conn.execute(
        'UPDATE requests SET verified = 0, verified_by = NULL, verified_at = NULL WHERE id = %s',
        (int(rid),),
    )
    conn.commit()
    print('Reset. You can verify it again now.')

conn.close()