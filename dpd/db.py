"""Thin PyMySQL wrapper. Raw SQL on purpose — no ORM."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pymysql
import pymysql.cursors

from .config import DBConfig


def connect(cfg: DBConfig):
    return pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        database=cfg.dbname,
        user=cfg.user,
        password=cfg.password,
        charset="utf8mb4",
        autocommit=False,
    )


@contextmanager
def cursor(conn, dict_rows: bool = True) -> Iterator[pymysql.cursors.Cursor]:
    cls = pymysql.cursors.DictCursor if dict_rows else pymysql.cursors.Cursor
    cur = conn.cursor(cls)
    try:
        yield cur
    finally:
        cur.close()
