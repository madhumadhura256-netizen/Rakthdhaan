import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import g

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
        )
        db.autocommit = True
    return db


def init_db():
    # Own connection, so it works outside a request/app context
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    try:
        with open(schema_path, "r") as f:
            with conn.cursor() as cur:
                cur.execute(f.read())
    finally:
        conn.close()


def close_db(e=None):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()