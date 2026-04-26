import base64
import hashlib
import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPES = "openid profile email offline_access"
AUTH_FILE = Path.home() / ".codex" / "auth.json"
REFRESH_BUFFER_SECONDS = 30


def _generate_pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _save(token_response: dict) -> None:
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "client_id": CLIENT_ID,
        "token_response": token_response,
        "expiration_timestamp": time.time() + token_response.get("expires_in", 3600),
    }
    AUTH_FILE.write_text(json.dumps(payload, indent=2))
    AUTH_FILE.chmod(0o600)


def _exchange_code(code: str, verifier: str) -> dict:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        },
    )
    resp.raise_for_status()
    return resp.json()


def _do_refresh(refresh_token: str) -> dict:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
        },
    )
    resp.raise_for_status()
    return resp.json()


def _browser_login() -> str:
    verifier, challenge = _generate_pkce()
    state = secrets.token_urlsafe(16)
    received: list[str] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/auth/callback":
                params = parse_qs(parsed.query)
                if "code" in params:
                    received.append(params["code"][0])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h1>Authenticated. You can close this tab.</h1>")

        def log_message(self, *_):
            pass

    auth_url = AUTHORIZE_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })

    print(f"Opening browser for OpenAI login...\nURL: {auth_url}")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 1455), _Handler)
    server.handle_request()
    server.server_close()

    if not received:
        raise RuntimeError("No authorization code received.")

    tokens = _exchange_code(received[0], verifier)
    _save(tokens)
    return tokens["access_token"]


def get_access_token() -> str:
    """Return a valid Bearer access token, refreshing or re-authenticating as needed."""
    if AUTH_FILE.exists():
        data = json.loads(AUTH_FILE.read_text())
        tokens = data.get("token_response", {})
        expiry = data.get("expiration_timestamp", 0)

        if time.time() < expiry - REFRESH_BUFFER_SECONDS:
            return tokens["access_token"]

        if rt := tokens.get("refresh_token"):
            try:
                new_tokens = _do_refresh(rt)
                _save(new_tokens)
                return new_tokens["access_token"]
            except httpx.HTTPError:
                pass  # fall through to full re-auth

    return _browser_login()
