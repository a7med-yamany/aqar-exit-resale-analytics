"""Verified TLS connections. Credentials never appear in reports or reprs."""
from contextlib import contextmanager
from dataclasses import dataclass, field
import ipaddress
import os
from pathlib import Path

from dotenv import dotenv_values
import pymysql

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    ca_file: Path

    @classmethod
    def from_env(cls, path=ROOT / '.env', *, environ=None):
        path = Path(path).resolve()
        values = {**dotenv_values(path), **(os.environ if environ is None else environ)}
        password = values.get('DB_PASSWORD', '')
        if not password:
            raise ValueError('Set DB_PASSWORD in the local .env file before connecting.')
        host = values.get('DB_HOST', 'aqarexit-mysql-aqarexit.i.aivencloud.com').strip()
        try:
            is_local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_local = False
        if not host or host.lower() in {'localhost', 'localhost.localdomain'} or is_local:
            raise ValueError('DB_HOST must identify the remote MySQL service.')
        port = int(values.get('DB_PORT', '27335'))
        if not 1 <= port <= 65535:
            raise ValueError('DB_PORT must be between 1 and 65535.')
        ca_file = Path(values.get('DB_SSL_CA', 'ca.pem'))
        if not ca_file.is_absolute():
            ca_file = path.parent / ca_file
        if not ca_file.is_file():
            raise ValueError('The DB_SSL_CA certificate file does not exist.')
        return cls(host, port, values.get('DB_NAME', 'aqar_exit'),
                   values.get('DB_USER', 'avnadmin'), password, ca_file)


def connect(settings=None):
    settings = settings or Settings.from_env()
    conn = pymysql.connect(
        host=settings.host, port=settings.port, database=settings.database,
        user=settings.user, password=settings.password, charset='utf8mb4',
        ssl_ca=str(settings.ca_file), ssl_verify_cert=True, ssl_verify_identity=True,
        autocommit=False, connect_timeout=15, read_timeout=60, write_timeout=30,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'")
            if not cur.fetchone()['Value']:
                raise RuntimeError('The server connection is not encrypted.')
        return conn
    except BaseException:
        conn.close()
        raise


@contextmanager
def transaction(settings=None):
    """Commit only on success; roll back and close on every other exit."""
    conn = connect(settings)
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
