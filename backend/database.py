import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import g

DATABASE_URL = os.environ.get("postgresql://raktdhan_user:iBlSRl2plM9yE9PMPawV3YAvjA1Couxo@dpg-dc590cmi0phs73cs81q0-a/raktdhan")

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        db.autocommit = True
    return db

def init_db():
    from flask import current_app
    with current_app.app_context():
        db = get_db()
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            with db.cursor() as cur:
                cur.execute(f.read())

def close_db(e=None):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()