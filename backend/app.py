import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db, close_db, get_db
from Migrations import ensure_donor_columns, ensure_donation_history_columns, refresh_donor_status
from auth import auth_bp
from donors import donors_bp
from requests_api import requests_bp
from bloodbank import bloodbank_bp
from alerts import alerts_bp
from transfers import transfers_bp
from otp import otp_bp
from Migrations import (
    ensure_donor_columns, ensure_donation_history_columns,
    ensure_request_columns, ensure_request_flow_tables, refresh_donor_status,
)
from hospital import hospital_bp
from flask_cors import CORS
import secrets
app = Flask(__name__)

CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)
app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'smart_blood.db')
CORS(app)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(donors_bp, url_prefix='/api/donors')
app.register_blueprint(requests_bp, url_prefix='/api/requests')
app.register_blueprint(bloodbank_bp, url_prefix='/api/bloodbank')
app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
app.register_blueprint(transfers_bp, url_prefix='/api/transfers')
app.register_blueprint(otp_bp)
app.register_blueprint(hospital_bp, url_prefix='/api/hospital')

@app.teardown_appcontext
def teardown_db(exception):
    close_db(exception)


@app.before_request
def reactivate_donors():
    if request.method == 'OPTIONS':
        return
    refresh_donor_status(get_db())

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


with app.app_context():
    init_db()
    try:
        ensure_donor_columns(get_db())
        ensure_donation_history_columns(get_db())
        refresh_donor_status(get_db())
    except Exception:
        pass
    ensure_request_columns(get_db())
    ensure_request_flow_tables(get_db())

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    