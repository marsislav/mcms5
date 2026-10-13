"""
search.sqlite - Unicode-aware, case-insensitive ``LIKE`` for SQLite.

Problem
-------
SQLite's built-in ``LIKE`` only ignores case for ASCII letters, so a Django
``icontains`` query for "софтуер" does NOT find "Софтуер" (Cyrillic, Greek,
accented Latin...). That would make the site search useless for Bulgarian.

Fix
---
On every new SQLite connection we replace SQLite's ``like()`` function with a
Python one that compares case-insensitively with full Unicode rules. Django's
``icontains``/``istartswith``... (and the admin's search boxes) then work for
any language. Other databases (PostgreSQL, MySQL) already do this correctly,
so nothing is changed for them.

SQLite evaluates ``X LIKE Y [ESCAPE E]`` as ``like(Y, X[, E])``.
"""
import re
from functools import lru_cache


@lru_cache(maxsize=512)
def _compile(pattern, escape):
    """Translate a LIKE pattern (%, _, escape char) to a compiled regex."""
    out, i = [], 0
    while i < len(pattern):
        ch = pattern[i]
        if escape and ch == escape and i + 1 < len(pattern):
            i += 1
            out.append(re.escape(pattern[i]))
        elif ch == '%':
            out.append('.*')
        elif ch == '_':
            out.append('.')
        else:
            out.append(re.escape(ch))
        i += 1
    return re.compile(''.join(out), re.IGNORECASE | re.DOTALL)


def _like(pattern, value, escape=None):
    if pattern is None or value is None:
        return None
    return 1 if _compile(str(pattern), escape).fullmatch(str(value)) else 0


def install_unicode_like(sender, connection, **kwargs):
    """``connection_created`` handler: register our ``like`` on SQLite connections."""
    if connection.vendor != 'sqlite':
        return
    connection.connection.create_function('like', 2, _like, deterministic=True)
    connection.connection.create_function('like', 3, _like, deterministic=True)
