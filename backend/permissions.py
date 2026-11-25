"""Convenience permission decorators.

Replaces your old second file (the one that defined its own token_required /
require_role). Nothing here imports from app.py, so there is no circular import.
Place @token_required ABOVE these decorators on every route.
"""
from auth import (
    token_required,
    role_required,
    STOCK_UPDATE_ROLES,
    DONATION_RECORD_ROLES,
    VERIFY_REQUEST_ROLES,
    VIEW_BANKS_ROLES,
)

# Backwards-compatible alias so old `from ... import require_role` still works
require_role = role_required


def can_update_stock(f):
    return role_required(*STOCK_UPDATE_ROLES)(f)


def can_record_donation(f):
    return role_required(*DONATION_RECORD_ROLES)(f)


def can_verify_request(f):
    return role_required(*VERIFY_REQUEST_ROLES)(f)


def can_view_banks(f):
    return role_required(*VIEW_BANKS_ROLES)(f)