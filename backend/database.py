import os

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import g, has_app_context

DATABASE_URL = os.environ.get("DATABASE_URL")


class DBWrapper:
    """
    Makes a psycopg2 connection behave like SQLite's connection,
    so old code like db.execute("... ?", (value,)) keeps working.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        # SQLite uses "?" placeholders, Postgres uses "%s"
        query = query.replace("?", "%s")
        cur = self._conn.cursor()
        cur.execute(query, params)
        return cur

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __getattr__(self, name):
        # Anything not defined above goes to the real connection
        return getattr(self._conn, name)


def _new_connection():
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
    )
    conn.autocommit = True
    return DBWrapper(conn)


def get_db():
    # Outside a Flask request/app context, give a standalone connection
    if not has_app_context():
        return _new_connection()

    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = _new_connection()
    return db


def init_db():
    # Uses its own connection, so it works at import time
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