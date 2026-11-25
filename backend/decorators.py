from functools import wraps
from flask import request, jsonify, g
import jwt
import os

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')

# Import role constants from auth
from auth import (
    STOCK_UPDATE_ROLES,
    DONATION_RECORD_ROLES,
    VERIFY_REQUEST_ROLES,
    VIEW_BANKS_ROLES
)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            g.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

def require_role(*allowed_roles):
    """Decorator for role-based access control"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            user_role = g.current_user.get('role')
            if user_role not in allowed_roles:
                return jsonify({
                    'error': f'Insufficient permissions. Required: {", ".join(allowed_roles)}. Your role: {user_role}'
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# Convenience decorators for common permission sets
def can_update_stock(f):
    return require_role(*STOCK_UPDATE_ROLES)(f)

def can_record_donation(f):
    return require_role(*DONATION_RECORD_ROLES)(f)

def can_verify_request(f):
    return require_role(*VERIFY_REQUEST_ROLES)(f)

def can_view_banks(f):
    return require_role(*VIEW_BANKS_ROLES)(f)