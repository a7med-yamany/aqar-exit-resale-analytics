"""Small exclusive-checkout pool for autocommit, read-only MySQL connections."""
from contextlib import contextmanager
from queue import LifoQueue,Empty
from threading import BoundedSemaphore,Lock
from time import monotonic


class ReadPool:
    def __init__(self,factory,*,max_size=4,wait_timeout=15,idle_timeout=120,
                 max_age=900,ping_after=30,clock=monotonic):
        self.factory=factory
        self.wait_timeout=wait_timeout
        self.idle_timeout=idle_timeout
        self.max_age=max_age
        self.ping_after=ping_after
        self.clock=clock
        self._idle=LifoQueue(max_size)
        self._slots=BoundedSemaphore(max_size)
        self._lock=Lock()
        self._closed=False

    @staticmethod
    def _discard(conn):
        try:conn.close()
        except Exception:pass

    @contextmanager
    def connection(self):
        if not self._slots.acquire(timeout=self.wait_timeout):
            raise TimeoutError('Read connections are busy. Please try again.')
        conn=None
        born=None
        reusable=False
        try:
            with self._lock:
                if self._closed:raise RuntimeError('Read pool is closed.')
                try:conn,born,last_used=self._idle.get_nowait()
                except Empty:pass
            now=self.clock()
            if conn is not None:
                if now-last_used>=self.idle_timeout or now-born>=self.max_age:
                    self._discard(conn);conn=None
                elif now-last_used>=self.ping_after:
                    try:conn.ping(reconnect=False)
                    except Exception:
                        self._discard(conn);conn=None
            if conn is None:
                conn=self.factory()
                born=self.clock()
            yield conn
            reusable=True
        finally:
            if conn is not None:
                with self._lock:
                    if reusable and not self._closed:
                        self._idle.put_nowait((conn,born,self.clock()))
                    else:self._discard(conn)
            self._slots.release()

    def close(self):
        with self._lock:
            self._closed=True
            while True:
                try:conn,_,_=self._idle.get_nowait()
                except Empty:break
                self._discard(conn)
