from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling
from flask import g

_pool = None
_config = None


def init_app(app):
    global _config
    _config = {
        "pool_name": "via_pool",
        "pool_size": app.config["MYSQL_POOL_SIZE"],
        "host": app.config["MYSQL_HOST"],
        "port": app.config["MYSQL_PORT"],
        "user": app.config["MYSQL_USER"],
        "password": app.config["MYSQL_PASSWORD"],
        "database": app.config["MYSQL_DB"],
        "charset": "utf8mb4",
        "autocommit": False,
    }
    app.teardown_appcontext(_close_conn)


def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(**_config)
    return _pool


def _get_conn():
    if "db_conn" not in g:
        g.db_conn = _get_pool().get_connection()
    return g.db_conn


def _close_conn(exception=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


def fetch_one(query, params=None):
    cur = _get_conn().cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        return cur.fetchone()
    finally:
        cur.close()


def fetch_all(query, params=None):
    cur = _get_conn().cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        return cur.fetchall()
    finally:
        cur.close()


def execute(query, params=None, commit=True):
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        if commit:
            conn.commit()
        return cur.lastrowid, cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


@contextmanager
def transaction():
    conn = _get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def executemany(query, seq_params, commit=True):
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.executemany(query, seq_params)
        if commit:
            conn.commit()
        return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
