"""Shelly Gen2+ prizleri, yerel RPC ile (§9.5): bulut ve hesap yok, istek ev ağında kalır.

Parola açıksa cihaz HTTP Digest (SHA-256) ister: ilk istek 401 ile `realm` ve `nonce` döner,
cevap parolayla hesaplanıp ikinci istekle gider. Parola yalnızca bu hesapta açılır; hata
metinlerine girmez. Kullanıcı adı Shelly'de sabittir.
"""

import asyncio
import hashlib
import json
import secrets
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from pydantic import SecretStr

from mayen.ports.switches import SwitchError, SwitchFailure

TIMEOUT_S = 5.0
USER = "admin"
SWITCH = 0  # prizde tek çıkış


class ShellyPlugs:
    def __init__(self, hosts: Mapping[str, str], password: SecretStr) -> None:
        self._hosts = dict(hosts)
        self._password = password

    async def set(self, name: str, on: bool) -> None:
        await asyncio.to_thread(self._rpc, name, "Switch.Set", {"id": SWITCH, "on": on})

    async def is_on(self, name: str) -> bool:
        reply = await asyncio.to_thread(self._rpc, name, "Switch.GetStatus", {"id": SWITCH})
        try:
            return bool(reply["output"])
        except (KeyError, TypeError) as e:
            raise SwitchError(SwitchFailure.UNAVAILABLE, f"unexpected reply: {e}") from e

    def _rpc(self, name: str, method: str, params: Mapping[str, Any]) -> Any:  # noqa: ANN401
        url = f"http://{self._hosts[name]}/rpc"
        body = json.dumps({"id": 1, "method": method, "params": dict(params)}).encode()
        try:
            try:
                return _post(url, body, None)
            except urllib.error.HTTPError as e:
                if e.code != 401:
                    raise
                challenge = e.headers.get("WWW-Authenticate", "")
            return _post(url, body, self._authorization(challenge))
        except urllib.error.HTTPError as e:
            failure = SwitchFailure.REJECTED if e.code == 401 else SwitchFailure.UNAVAILABLE
            raise SwitchError(failure, f"{name}: device said {e.code}") from None
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            reason = getattr(e, "reason", type(e).__name__)
            detail = f"{name}: unreachable: {reason}"
            raise SwitchError(SwitchFailure.UNAVAILABLE, detail) from None

    def _authorization(self, challenge: str) -> str:
        fields = _fields(challenge)
        realm, nonce = fields.get("realm", ""), fields.get("nonce", "")
        cnonce = secrets.token_hex(8)
        ha1 = _sha(f"{USER}:{realm}:{self._password.get_secret_value()}")
        ha2 = _sha("POST:/rpc")
        response = _sha(f"{ha1}:{nonce}:00000001:{cnonce}:auth:{ha2}")
        return (
            f'Digest username="{USER}", realm="{realm}", nonce="{nonce}", uri="/rpc", '
            f'algorithm=SHA-256, response="{response}", qop=auth, nc=00000001, '
            f'cnonce="{cnonce}"'
        )


def _post(url: str, body: bytes, authorization: str | None) -> Any:  # noqa: ANN401
    headers = {"Content-Type": "application/json"}
    if authorization is not None:
        headers["Authorization"] = authorization
    request = urllib.request.Request(url, body, headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as reply:
        payload = json.load(reply)
    if "error" in payload:
        raise SwitchError(SwitchFailure.UNAVAILABLE, f"device error: {payload['error']}")
    return payload["result"]


def _fields(challenge: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in challenge.removeprefix("Digest ").split(","):
        key, _, value = part.strip().partition("=")
        out[key] = value.strip('"')
    return out


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
