"""Cihaz kimliği Tailscale'den (§10.1): bağlantının hangi düğümden geldiğini Tailscale doğrular.

Kimlik düğümün kalıcı kimliğidir (`StableID`); ad değişebilir, kalıcı kimlik değişmez.
Tailscale kapalıysa, adres tailnet'ten değilse ya da sorgu başarısızsa bağlantı doğrulanmamış
sayılır: sessizce güvenilen bir hata, beyan edilmiş bir kimlikten farksızdır.
"""

import asyncio
import json
import logging

from mayen.ports.people import DeviceId

log = logging.getLogger(__name__)

WHOIS_TIMEOUT_S = 2.0


class TailscaleIdentity:
    def __init__(self, command: str = "tailscale") -> None:
        self._command = command

    async def device(self, address: str) -> DeviceId | None:
        try:
            process = await asyncio.create_subprocess_exec(
                self._command,
                "whois",
                "--json",
                address,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError as e:
            log.warning("tailscale whois could not start: %s", e)
            return None
        try:
            out, _ = await asyncio.wait_for(process.communicate(), WHOIS_TIMEOUT_S)
        except TimeoutError:
            process.kill()
            await process.wait()
            log.warning("tailscale whois timed out for %s", address)
            return None
        if process.returncode != 0:
            return None
        try:
            stable_id = json.loads(out)["Node"]["StableID"]
        except (json.JSONDecodeError, KeyError, TypeError):
            log.warning("tailscale whois gave an unexpected answer for %s", address)
            return None
        return DeviceId(stable_id) if isinstance(stable_id, str) and stable_id else None
