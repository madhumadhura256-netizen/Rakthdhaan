DONOR_COLUMNS = {
    'aadhaar': 'TEXT',
    'weight': 'REAL',
    'previous_hb': 'REAL',
    'diseases': "TEXT DEFAULT 'None'",
    'bad_habits': "TEXT DEFAULT 'None'",
    'disorders': "TEXT DEFAULT 'None'",
    'sms_consent': 'INTEGER DEFAULT 0',
}


def ensure_donor_columns(db):
    existing = {r[1] for r in db.execute('PRAGMA table_info(donors)').fetchall()}
    for col, decl in DONOR_COLUMNS.items():
        if col not in existing:
            db.execute(f'ALTER TABLE donors ADD COLUMN {col} {decl}')
    db.commit()
def ensure_donation_history_columns(db):
    """Adds the new donor columns if they are missing."""
    existing = {row['name'] for row in db.execute('PRAGMA table_info(donors)')}

    if 'has_donated_before' not in existing:
        db.execute('ALTER TABLE donors ADD COLUMN has_donated_before INTEGER DEFAULT 0')
        # Old donors who already have a last donation date count as "donated before"
        db.execute('UPDATE donors SET has_donated_before = 1 WHERE last_donation_date IS NOT NULL')

    if 'next_eligible_date' not in existing:
        db.execute('ALTER TABLE donors ADD COLUMN next_eligible_date TEXT')

    db.commit()


def refresh_donor_status(db):
    """Donors whose rest period is over become active again."""
    db.execute(
        "UPDATE donors SET status = 'active' "
        "WHERE status = 'inactive' AND next_eligible_date IS NOT NULL "
        "AND next_eligible_date <= date('now')"
    )
    db.commit()

def ensure_request_flow_tables(db):
    """Which blood banks each request was sent to, and how they answered."""
    db.execute('''
        CREATE TABLE IF NOT EXISTS request_bank_notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
            blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id) ON DELETE CASCADE,
            distance_km REAL,
            status TEXT DEFAULT 'notified'
                CHECK (status IN ('notified', 'accepted', 'declined', 'fulfilled')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            responded_at TEXT,
            UNIQUE (request_id, blood_bank_id)
        )
    ''')
    db.execute(
        'CREATE INDEX IF NOT EXISTS idx_notices_bank ON request_bank_notices(blood_bank_id)'
    )
    db.commit()