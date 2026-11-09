"""Sign-in through Market Hub.

A member of Bot League is a member of Market Hub: the same account, signed in on the portal. With
HUB_URL and HUB_SESSION_SECRET set, the service reads the hub's session cookie (``mh_session``,
shared on the parent domain) and checks its signature with the hub's secret. It never sets or
changes that cookie. Unlike the tools, the site is open to visitors: the pages and the board can
be read signed out, and only the member's own routes need a session.

The Bot League phone app has no cookie: it signs in at the hub's ``/api/app/auth/...`` and holds
the token the hub hands it (``market-hub-landing/src/markethub/tokens.py``), signed with the same
secret under a salt of its own. It sends it as ``Authorization: Bearer <token>``, and a request that
carries one is the token's user or nobody: the cookie is not looked at, so a token never borrows a
browser's session. A bot key (``mhb_...``) is not a token: the agent's routes read it, never this.

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
MAX_AGE = 30 * 86400  # the hub's session length, and its app token's
APP_TOKEN_SALT = "markethub.app-token"  # as in the hub's tokens.py
AGENT_KEY_PREFIX = "mhb_"  # engine.KEY_PREFIX: a bot key, not a sign-in
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


def app_token(request: Request) -> str | None:
    """The hub's app token an ``Authorization: Bearer`` header carries, or None (none, or a bot key)."""
    scheme, _, value = (request.headers.get("authorization") or "").partition(" ")
    value = value.strip()
    if scheme.lower() != "bearer" or not value or value.startswith(AGENT_KEY_PREFIX):
        return None
    return value


def read_token(token: str | None, secret: str, max_age: int = MAX_AGE) -> dict | None:
    """The user a hub app token was issued to, or None: not the hub's, changed, or run out."""
    if not token:
        return None
    try:
        user = itsdangerous.URLSafeTimedSerializer(secret, salt=APP_TOKEN_SALT).loads(token, max_age=max_age)
    except itsdangerous.BadData:
        return None
    return user if isinstance(user, dict) and user.get("id") else None


class Hub:
    def __init__(self, hub: tuple[str, str] | None):
        self.url, self.secret = (hub[0].rstrip("/"), hub[1]) if hub else (None, None)

    def user(self, request: Request) -> dict | None:
        token = app_token(request)
        if self.secret:
            return read_token(token, self.secret) if token else read_user(request.cookies.get(COOKIE), self.secret)
        visitor = request.query_params.get("visitor") == "1" or request.cookies.get("bl_visitor") == "1"
        return None if visitor else LOCAL_USER

    def from_app(self, request: Request) -> bool:
        """Whether a request carries a good app token. Such a request needs no Origin: what that check
        stops is a foreign page using the cookie a browser sends by itself, and a page cannot add
        this header. A local run takes any token, as it takes anyone."""
        token = app_token(request)
        return bool(token) and (self.secret is None or read_token(token, self.secret) is not None)

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
