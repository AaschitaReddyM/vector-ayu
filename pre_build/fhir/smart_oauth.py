"""
SMART-on-FHIR OAuth Launch (Spec §6).

The EHR launches our app inside its chart frame (the `iss` and `launch`
params arrive on the launch URL). We then do the standard SMART App Launch
OAuth 2.0 / PKCE dance:

    EHR  ──(launch URL with iss, launch)──▶  ClimaHealth Launch endpoint
    ClimaHealth ──(authorize?response_type=code&...)──▶  EHR Auth Server
    EHR Auth Server ──(redirect code)──▶  ClimaHealth Redirect URI
    ClimaHealth ──(POST token grant)──▶  EHR Token Endpoint
    EHR Token Endpoint ──(access_token + id_token + patient + scope)──▶  ClimaHealth

This module ships the *URL builders and an in-memory token store* so the
buildathon team can wire it to live sandboxes (e.g. launch.smarthealthit.org
or Epic on FHIR) on Day 1 of the event without rewriting the contract.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode


# ── Config ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SmartLaunchConfig:
    """Static config for one EHR integration (one record per Epic/Cerner customer)."""
    client_id: str
    redirect_uri: str
    scope: str = (
        "launch openid fhirUser "
        "patient/Patient.read patient/Observation.read patient/MedicationRequest.read "
        "patient/DocumentReference.write"
    )
    aud_iss: str = ""  # set per-launch from the EHR's `iss` param


@dataclass(frozen=True)
class LaunchContext:
    """The pair the EHR hands us at launch time."""
    iss: str       # FHIR base URL of the EHR — also our `aud` claim
    launch: str    # opaque launch token, round-tripped to the auth endpoint


# ── PKCE ───────────────────────────────────────────────────────────────────

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) per RFC 7636."""
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


# ── In-memory session store ────────────────────────────────────────────────

@dataclass
class PendingLaunch:
    state: str
    code_verifier: str
    iss: str
    launch: str
    created_at: float


@dataclass
class IssuedToken:
    access_token: str
    token_type: str
    expires_at: float
    patient: str | None
    scope: str
    refresh_token: str | None = None


@dataclass
class SmartSession:
    """One in-memory session keyed by state. Swap for Redis/Postgres in prod."""
    pending: dict[str, PendingLaunch] = field(default_factory=dict)
    issued: dict[str, IssuedToken] = field(default_factory=dict)

    def stash(self, launch_ctx: LaunchContext) -> tuple[str, str]:
        """Begin a launch — returns (state, code_challenge)."""
        verifier, challenge = generate_pkce_pair()
        state = _b64url(secrets.token_bytes(16))
        self.pending[state] = PendingLaunch(
            state=state,
            code_verifier=verifier,
            iss=launch_ctx.iss,
            launch=launch_ctx.launch,
            created_at=time.time(),
        )
        return state, challenge

    def consume(self, state: str) -> PendingLaunch:
        if state not in self.pending:
            raise KeyError(f"unknown SMART launch state: {state}")
        return self.pending.pop(state)

    def remember(self, key: str, token: IssuedToken) -> None:
        self.issued[key] = token


# ── URL builders ───────────────────────────────────────────────────────────

def build_authorize_url(
    *,
    authorize_endpoint: str,
    cfg: SmartLaunchConfig,
    launch_ctx: LaunchContext,
    state: str,
    code_challenge: str,
) -> str:
    """The 302 we send the user-agent to after the EHR launches us."""
    params = {
        "response_type": "code",
        "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri,
        "scope": cfg.scope,
        "state": state,
        "aud": launch_ctx.iss,
        "launch": launch_ctx.launch,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{authorize_endpoint}?{urlencode(params)}"


def build_token_request(
    *,
    cfg: SmartLaunchConfig,
    code: str,
    code_verifier: str,
) -> dict[str, str]:
    """Body of the POST to the EHR's token endpoint."""
    return {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg.redirect_uri,
        "client_id": cfg.client_id,
        "code_verifier": code_verifier,
    }


# ── Stub token issuer (offline demo) ───────────────────────────────────────

def issue_demo_token(*, patient: str, scope: str, ttl_seconds: int = 3600) -> IssuedToken:
    """Issue a fake bearer for offline buildathon demos.

    Replace with a real POST to ``{iss}/oauth2/token`` once on a live network.
    """
    return IssuedToken(
        access_token=_b64url(secrets.token_bytes(24)),
        token_type="Bearer",
        expires_at=time.time() + ttl_seconds,
        patient=patient,
        scope=scope,
        refresh_token=_b64url(secrets.token_bytes(16)),
    )


if __name__ == "__main__":
    cfg = SmartLaunchConfig(
        client_id="climahealth-dev",
        redirect_uri="https://climahealth.local/smart/callback",
    )
    launch_ctx = LaunchContext(
        iss="https://launch.smarthealthit.org/v/r4/fhir",
        launch="abc.launch.token",
    )
    sess = SmartSession()
    state, challenge = sess.stash(launch_ctx)
    url = build_authorize_url(
        authorize_endpoint="https://launch.smarthealthit.org/v/r4/auth/authorize",
        cfg=cfg,
        launch_ctx=launch_ctx,
        state=state,
        code_challenge=challenge,
    )
    print(f"  authorize URL: {url[:140]}...")
    token = issue_demo_token(patient="PT-0001", scope=cfg.scope)
    sess.remember(state, token)
    print(f"  demo token   : {token.access_token[:24]}... expires in {token.expires_at - time.time():.0f}s")
