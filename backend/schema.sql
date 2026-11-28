CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('donor','requester','blood_bank','hospital','admin','doctor','paramedical','blood_connect')),
    phone TEXT,
    city TEXT,
    verified INTEGER DEFAULT 0,
    verified_by TEXT,
    verified_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS donors (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    blood_group TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    gender TEXT NOT NULL CHECK (gender IN ('Male','Female','Other')),
    age INTEGER NOT NULL CHECK (age >= 18 AND age <= 65),
    phone TEXT NOT NULL,
    aadhaar TEXT,
    mobile_verified INTEGER DEFAULT 0,
    sms_consent INTEGER DEFAULT 0,
    weight REAL,
    previous_hb REAL,
    diseases TEXT,
    bad_habits TEXT,
    disorders TEXT,
    pincode TEXT,
    latitude REAL,
    longitude REAL,
    city TEXT,
    last_donation_date TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','inactive','cooldown')),
    cooldown_months INTEGER DEFAULT 3,
    total_requests_responded INTEGER DEFAULT 0,
    avg_response_minutes REAL DEFAULT 0,
    is_rare_group INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 0,
    has_donated_before INTEGER DEFAULT 0,
    next_eligible_date TEXT,
    total_units_donated INTEGER DEFAULT 0,
    donation_codes TEXT DEFAULT '[]',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blood_banks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    hospital_name TEXT,
    doctor_id TEXT,
    license_number TEXT,
    address TEXT,
    city TEXT,
    pincode TEXT,
    latitude REAL,
    longitude REAL,
    phone TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hospitals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hospital_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    address TEXT,
    city TEXT,
    pincode TEXT,
    latitude REAL,
    longitude REAL,
    phone TEXT,
    email TEXT,
    license_number TEXT,
    license_document TEXT,
    verified INTEGER DEFAULT 0,
    verified_by TEXT,
    verified_at TEXT,
    verification_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hospital_blood_stock (
    id SERIAL PRIMARY KEY,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    units_available INTEGER DEFAULT 0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hospital_id, blood_group)
);

CREATE TABLE IF NOT EXISTS blood_stock (
    id SERIAL PRIMARY KEY,
    blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    units_available INTEGER DEFAULT 0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(blood_bank_id, blood_group)
);

CREATE TABLE IF NOT EXISTS requests (
    id SERIAL PRIMARY KEY,
    requester_id INTEGER REFERENCES users(id),
    patient_name TEXT NOT NULL,
    hospital_name TEXT NOT NULL,
    doctor_id TEXT NOT NULL,
    nurse_id TEXT,
    paramedic_id TEXT,
    blood_group TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    units_needed INTEGER DEFAULT 1,
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('critical','urgent','normal')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','fulfilled','cancelled')),
    latitude REAL,
    longitude REAL,
    city TEXT,
    pincode TEXT,
    verified INTEGER DEFAULT 0,
    verified_by TEXT,
    verified_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS donations (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES requests(id),
    donor_id INTEGER NOT NULL REFERENCES donors(id),
    blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id),
    donation_date TEXT NOT NULL,
    units INTEGER DEFAULT 1,
    status TEXT DEFAULT 'completed' CHECK (status IN ('completed','pending','cancelled')),
    confirmed_by TEXT,
    confirmed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    certificate_code TEXT
);

CREATE TABLE IF NOT EXISTS alerts_sent (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    donor_id INTEGER NOT NULL REFERENCES donors(id) ON DELETE CASCADE,
    channel TEXT DEFAULT 'push' CHECK (channel IN ('push','sms')),
    status TEXT DEFAULT 'sent' CHECK (status IN ('sent','delivered','accepted','declined','failed')),
    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
    responded_at TEXT
);

CREATE TABLE IF NOT EXISTS blood_transfers (
    id SERIAL PRIMARY KEY,
    from_bank_id INTEGER NOT NULL REFERENCES blood_banks(id),
    to_bank_id INTEGER NOT NULL REFERENCES blood_banks(id),
    blood_group TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    units_needed INTEGER NOT NULL DEFAULT 1,
    urgency TEXT DEFAULT 'normal' CHECK (urgency IN ('critical','urgent','normal')),
    distance_km REAL,
    estimated_time_hours REAL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','approved','in_transit','completed','cancelled')),
    requester_id INTEGER NOT NULL REFERENCES users(id),
    requester_notes TEXT,
    approved_by TEXT,
    approved_at TEXT,
    dispatched_by TEXT,
    dispatched_at TEXT,
    courier_name TEXT,
    courier_phone TEXT,
    vehicle_number TEXT,
    expected_arrival TEXT,
    received_by TEXT,
    received_at TEXT,
    received_units INTEGER,
    condition TEXT DEFAULT 'good' CHECK (condition IN ('good','damaged','temperature_issue')),
    receiver_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stock_reservations (
    id SERIAL PRIMARY KEY,
    transfer_id INTEGER NOT NULL REFERENCES blood_transfers(id),
    blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id),
    blood_group TEXT NOT NULL CHECK (blood_group IN ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    units_reserved INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hospital_sms_log (
    id SERIAL PRIMARY KEY,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    blood_group TEXT NOT NULL,
    donors_count INTEGER NOT NULL,
    message TEXT NOT NULL,
    sent_by INTEGER NOT NULL REFERENCES users(id),
    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent' CHECK (status IN ('sent','partial','failed'))
);

CREATE TABLE IF NOT EXISTS request_bank_notices (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id) ON DELETE CASCADE,
    distance_km REAL,
    status TEXT DEFAULT 'notified' CHECK (status IN ('notified', 'accepted', 'declined', 'fulfilled')),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    responded_at TEXT,
    UNIQUE (request_id, blood_bank_id)
);

CREATE INDEX IF NOT EXISTS idx_donors_bg ON donors(blood_group);
CREATE INDEX IF NOT EXISTS idx_donors_status ON donors(status);
CREATE INDEX IF NOT EXISTS idx_donors_pincode ON donors(pincode);
CREATE INDEX IF NOT EXISTS idx_donors_city ON donors(city);
CREATE INDEX IF NOT EXISTS idx_requests_bg ON requests(blood_group);
CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_requester ON requests(requester_id);
CREATE INDEX IF NOT EXISTS idx_stock_bg ON blood_stock(blood_group);
CREATE INDEX IF NOT EXISTS idx_alerts_request ON alerts_sent(request_id);
CREATE INDEX IF NOT EXISTS idx_transfers_status ON blood_transfers(status);
CREATE INDEX IF NOT EXISTS idx_transfers_from_bank ON blood_transfers(from_bank_id);
CREATE INDEX IF NOT EXISTS idx_transfers_to_bank ON blood_transfers(to_bank_id);
CREATE INDEX IF NOT EXISTS idx_transfers_blood_group ON blood_transfers(blood_group);
CREATE INDEX IF NOT EXISTS idx_users_verified ON users(verified);
CREATE INDEX IF NOT EXISTS idx_hospitals_hospital_id ON hospitals(hospital_id);
CREATE INDEX IF NOT EXISTS idx_hospitals_city ON hospitals(city);
CREATE INDEX IF NOT EXISTS idx_hospital_stock_hospital ON hospital_blood_stock(hospital_id);
CREATE INDEX IF NOT EXISTS idx_hospital_sms_log_hospital ON hospital_sms_log(hospital_id);