"""Exclusive pooled reads; writes keep fresh transaction-owned connections."""
import atexit
from functools import lru_cache
import pymysql
from db import connect, transaction
from read_pool import ReadPool
from repository import Repository

READ_METHODS = {'lookup_options','overview_counts','top_projects','project_statistics',
                'project_reviews','area_properties','search_properties','top_developers',
                'contract_properties','market_summary','listing_details'}


def _read_connection():
    conn = connect()
    try:
        conn.autocommit(True)
        with conn.cursor() as cur:
            cur.execute('SET SESSION TRANSACTION READ ONLY')
        return conn
    except BaseException:
        conn.close()
        raise


@lru_cache(maxsize=1)
def _pool():
    pool=ReadPool(_read_connection)
    atexit.register(pool.close)
    return pool


def read(method,*args):
    if method not in READ_METHODS:
        raise ValueError('Unsupported read operation.')
    for attempt in range(2):
        try:
            with _pool().connection() as conn:
                return getattr(Repository(conn),method)(*args)
        except (pymysql.OperationalError,pymysql.InterfaceError) as exc:
            if attempt or exc.args[0] not in (0,2006,2013):raise


def reset_pool():
    if _pool.cache_info().currsize:
        _pool().close()
        _pool.cache_clear()


def register(*args):
    with transaction() as conn:
        return Repository(conn).register_user(*args)


def review(*args):
    with transaction() as conn:
        Repository(conn).add_review(*args)
