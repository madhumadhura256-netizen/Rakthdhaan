from flask import Blueprint, jsonify
from auth import token_required

transfers_bp = Blueprint('transfers', __name__)


@transfers_bp.route('', methods=['GET'])
@transfers_bp.route('/', methods=['GET'])
@token_required
def list_transfers():
    return jsonify([])
