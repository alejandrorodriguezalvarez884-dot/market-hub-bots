"""Sign-in through Market Hub.

A member of Bot League is a member of Market Hub: the same account, signed in on the portal. With
HUB_URL and HUB_SESSION_SECRET set, the service reads the hub's session cookie (``mh_session``,
shared on the parent domain) and checks its signature with the hub's secret. It never sets or
changes that cookie. Unlike the tools, the site is open to visitors: the pages and the board can
be read signed out, and only the member's own routes need a session.

Without the two settings (a local run) everyone is one local member, unless the request carries
``?visitor=1`` or the cookie ``bl_visitor=1``, so the signed-out site can be seen too.
"""

from __future__ import annotations

import json
import os
from base64 import b64decode
from urllib.parse import quote, urlsplit

import itsdangerous
from starlette.requests import Request

COOKIE = "mh_session"
MAX_AGE = 30 * 86400  # the hub's session length
LOCAL_USER = {"id": "local", "email": "", "name": "Local member", "picture": ""}


def settings() -> tuple[str, str] | None:
    hub = os.environ.get("HUB_URL", "").strip().rstrip("/")
    secret = os.environ.get("HUB_SESSION_SECRET", "").strip()
    return (hub, secret) if hub and secret else None


def read_user(cookie: str | None, secret: str, max_age: int = MAX_AGE) -> dict | None:
    """The user in a hub session cookie, or None if it is missing, forged or expired."""
    if not cookie:
        return None
    try:
        data = itsdangerous.TimestampSigner(secret).unsign(cookie.encode(), max_age=max_age)
        user = json.loads(b64decode(data)).get("user")
    except (itsdangerous.BadSignature, ValueError, TypeError, AttributeError):
        return None
    return user if isinstance(user, dict) and user.get("id") else None


class Hub:
    def __init__(self, hub: tuple[str, str] | None):
        self.url, self.secret = (hub[0].rstrip("/"), hub[1]) if hub else (None, None)

    def user(self, request: Request) -> dict | None:
        if self.secret:
            return read_user(request.cookies.get(COOKIE), self.secret)
        visitor = request.query_params.get("visitor") == "1" or request.cookies.get("bl_visitor") == "1"
        return None if visitor else LOCAL_USER

    def signin_url(self, request: Request, path: str | None = None) -> str | None:
        """The hub's sign-in, coming back here afterwards: to ``path`` on this site, or for an API
        call to the page that made it (its Referer, when it is this same site)."""
        if not self.url:
            return None
        scheme = "https" if self.url.startswith("https:") else request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        referer = request.headers.get("referer", "")
        if path:
            here = f"{scheme}://{host}{path}"
        elif urlsplit(referer).netloc == host:
            here = referer
        else:
            here = f"{scheme}://{host}/"
        return f"{self.url}/signin/?next={quote(here, safe='')}"
