from flask import Blueprint, jsonify, request, g
from matching import alert_donors
from database import get_db
from decorators import (
    token_required,
    can_update_stock,
    can_record_donation,
    can_verify_request,
    can_view_banks
)
from datetime import datetime, timedelta
import uuid

bloodbank_bp = Blueprint('bloodbank', __name__)

def _bank_row_to_dict(row):
    return {
        'id': row['id'],
        'user_id': row['user_id'],
        'name': row['name'],
        'hospital_name': row['hospital_name'],
        'doctor_id': row['doctor_id'],
        'license_number': row['license_number'],
        'address': row['address'],
        'city': row['city'],
        'pincode': row['pincode'],
        'latitude': row['latitude'],
        'longitude': row['longitude'],
        'phone': row['phone'],
    }

@bloodbank_bp.route('/banks', methods=['GET'])
@token_required
@can_view_banks
def list_banks():
    db = get_db()
    city = request.args.get('city')
    pincode = request.args.get('pincode')
    query = 'SELECT * FROM blood_banks'
    params = []
    conditions = []
    if city:
        conditions.append('city = ?')
        params.append(city)
    if pincode:
        conditions.append('pincode = ?')
        params.append(pincode)
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    rows = db.execute(query, params).fetchall()
    return jsonify([_bank_row_to_dict(r) for r in rows])

@bloodbank_bp.route('/stock', methods=['GET'])
@token_required
@can_view_banks
def get_stock():
    db = get_db()
    blood_bank_id = request.args.get('blood_bank_id')
    blood_group = request.args.get('blood_group')

    query = 'SELECT * FROM blood_stock WHERE 1=1'
    params = []
    if blood_bank_id:
        query += ' AND blood_bank_id = ?'
        params.append(blood_bank_id)
    if blood_group:
        query += ' AND blood_group = ?'
        params.append(blood_group)
    rows = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])

@bloodbank_bp.route('/stock', methods=['POST'])
@token_required
@can_update_stock
def update_stock():
    """Only admin, doctor, paramedical, blood_connect can update stock"""
    db = get_db()
    data = request.get_json() or {}
    blood_bank_id = data.get('blood_bank_id')
    blood_group = data.get('blood_group')
    units_available = data.get('units_available')

    if not all([blood_bank_id, blood_group, units_available is not None]):
        return jsonify({'error': 'blood_bank_id, blood_group, units_available required'}), 400

    if not isinstance(units_available, int) or units_available < 0:
        return jsonify({'error': 'units_available must be a non-negative integer'}), 400

    existing = db.execute(
        'SELECT id FROM blood_stock WHERE blood_bank_id = ? AND blood_group = ?',
        (blood_bank_id, blood_group)
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE blood_stock SET units_available = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?',
            (units_available, existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO blood_stock (blood_bank_id, blood_group, units_available) VALUES (?, ?, ?)',
            (blood_bank_id, blood_group, units_available)
        )
    db.commit()
    return jsonify({'message': 'Stock updated successfully'})

def _generate_certificate_code():
    """Generate a unique certificate code like RKT-2024-ABC123"""
    from datetime import datetime
    year = datetime.now().year
    unique = uuid.uuid4().hex[:6].upper()
    return f"RKT-{year}-{unique}"

@bloodbank_bp.route('/donation', methods=['POST'])
@token_required
@can_record_donation
def record_donation():
    """Only admin, doctor, paramedical, blood_connect can record donations"""
    db = get_db()
    data = request.get_json() or {}

    donor_id = data.get('donor_id')
    blood_bank_id = data.get('blood_bank_id')
    request_id = data.get('request_id')
    units = data.get('units', 1)
    donation_date = data.get('donation_date')
    confirmed_by = data.get('confirmed_by', g.current_user.get('email', ''))

    if not all([donor_id, blood_bank_id, donation_date]):
        return jsonify({'error': 'donor_id, blood_bank_id, donation_date required'}), 400

    donor = db.execute('SELECT * FROM donors WHERE id = ?', (donor_id,)).fetchone()
    if not donor:
        return jsonify({'error': 'Donor not found'}), 404

    # Check if donor is eligible (active status)
    if donor['status'] != 'active':
        return jsonify({'error': f'Donor is not active (current status: {donor["status"]})'}), 400

    cooldown_months = donor['cooldown_months'] or (3 if donor['gender'] == 'Male' else 4)
    try:
        donation_dt = datetime.strptime(donation_date, '%Y-%m-%d')
    except ValueError:
        donation_dt = datetime.now()

    reactivate_date = (donation_dt + timedelta(days=cooldown_months * 30)).strftime('%Y-%m-%d')

    # Generate unique certificate code for this donation
    certificate_code = _generate_certificate_code()

    # Mark donor inactive/cooldown
    db.execute(
        'UPDATE donors SET status = ?, last_donation_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        ('inactive', donation_date, donor_id)
    )

    # Record donation with certificate code
    db.execute(
        '''INSERT INTO donations (request_id, donor_id, blood_bank_id, donation_date, units, confirmed_by, certificate_code)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (request_id, donor_id, blood_bank_id, donation_date, units, confirmed_by, certificate_code)
    )

    # Add stock to blood bank
    donor_bg = donor['blood_group']
    existing = db.execute(
        'SELECT id FROM blood_stock WHERE blood_bank_id = ? AND blood_group = ?',
        (blood_bank_id, donor_bg)
    ).fetchone()
    if existing:
        db.execute(
            'UPDATE blood_stock SET units_available = units_available + ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?',
            (units, existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO blood_stock (blood_bank_id, blood_group, units_available) VALUES (?, ?, ?)',
            (blood_bank_id, donor_bg, units)
        )

    db.commit()
    return jsonify({
        'message': 'Donation recorded successfully',
        'donor_id': donor_id,
        'status': 'inactive',
        'cooldown_months': cooldown_months,
        'eligible_again_after': reactivate_date,
        'certificate_code': certificate_code,
        'units_donated': units
    }), 201

@bloodbank_bp.route('/reactivate-donors', methods=['POST'])
@token_required
@can_record_donation
def reactivate_donors():
    """Auto-reactivate donors whose cooldown has expired"""
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    cursor = db.execute('SELECT id, name, last_donation_date, cooldown_months FROM donors WHERE status = ?', ('inactive',))
    inactive = cursor.fetchall()

    reactivated = []
    for d in inactive:
        if not d['last_donation_date']:
            continue
        try:
            donation_dt = datetime.strptime(d['last_donation_date'], '%Y-%m-%d')
        except ValueError:
            continue
        cooldown = d['cooldown_months'] or 3
        reactivate_dt = donation_dt + timedelta(days=cooldown * 30)
        if reactivate_dt.strftime('%Y-%m-%d') <= today:
            db.execute('UPDATE donors SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', ('active', d['id']))
            reactivated.append({'id': d['id'], 'name': d['name']})

    db.commit()
    return jsonify({'message': f'Reactivated {len(reactivated)} donors', 'donors': reactivated})