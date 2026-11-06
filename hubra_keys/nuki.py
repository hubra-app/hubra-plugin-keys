"""Nuki Web API: keypad codes and opening a lock.

https://api.nuki.io with the club's API token (Nuki Web → API). Only that
host is called, so there is no address to check.
"""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.nuki.io"
TIMEOUT = 15
# Nuki authorization type of a keypad code.
KEYPAD = 13


class NukiError(Exception):
    pass


def _call(token: str, method: str, path: str, body=None):
    if not token:
        raise NukiError("No Nuki API token in the Keys settings.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise NukiError("Nuki refused the API token.") from None
        if exc.code == 404:
            raise NukiError("Nuki does not know this lock.") from None
        raise NukiError(f"Nuki answered {exc.code}.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise NukiError("Nuki could not be reached.") from None
    return json.loads(raw) if raw else None


def new_code() -> str:
    """Six digits 1–9 that do not start with 12, as Nuki keypads require."""
    while True:
        code = "".join(secrets.choice("123456789") for _ in range(6))
        if not code.startswith("12"):
            return code


def add_code(token: str, smartlock_id: int, name: str, code: str) -> str:
    """Adds a keypad code and returns Nuki's id for it."""
    _call(
        token,
        "PUT",
        f"/smartlock/{smartlock_id}/auth",
        {"name": name, "type": KEYPAD, "code": int(code), "remoteAllowed": False},
    )
    # Nuki does not answer with the id; find the code by its name.
    for auth in _call(token, "GET", f"/smartlock/{smartlock_id}/auth") or []:
        if auth.get("name") == name and auth.get("type") == KEYPAD:
            return str(auth.get("id"))
    raise NukiError("Nuki did not keep the keypad code.")


def remove_code(token: str, smartlock_id: int, auth_id: str) -> None:
    try:
        _call(
            token,
            "DELETE",
            f"/smartlock/{smartlock_id}/auth/{urllib.parse.quote(auth_id, safe='')}",
        )
    except NukiError as exc:
        if "does not know" not in str(exc):  # gone already
            raise


def unlock(token: str, smartlock_id: int) -> None:
    _call(token, "POST", f"/smartlock/{smartlock_id}/action/unlock")
