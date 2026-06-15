"""
Dual-Track Compliance Engine (Spec §7).

Compliance with HIPAA and TCPA dictates explicit digital consent before
live geospatial telemetry or automated SMS. We support BOTH tracks so the
platform still works on patients who decline the app:

    Track A — Fully Consented (automated pipeline)
        H3 background tracking, smart-device vitals, automated 48-hour SMS

    Track B — Non-Consented (internal triage only)
        Under HIPAA Privacy Rule's "Healthcare Operations" provision,
        the health system may still process records + billing ZIP for
        population care coordination. The flag still shows up on the
        72-hour dashboard; outreach is a manual clinician phone call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ConsentTrack(str, Enum):
    A_FULL = "A"   # full consent: telemetry + SMS
    B_OPS = "B"    # ops-only: ZIP-level triage, no SMS, no device data


@dataclass(frozen=True)
class ConsentRecord:
    patient_id: str
    track: ConsentTrack
    signed_at: datetime | None    # None for Track B (no signature exists)
    privacy_policy_version: str
    telemetry_optin: bool         # only True if Track A
    sms_optin: bool               # only True if Track A
    geo_optin: bool               # only True if Track A


@dataclass(frozen=True)
class WorkflowPlan:
    """The downstream contract — tells every other module what it may do."""
    track: ConsentTrack
    may_ingest_device_telemetry: bool
    may_send_automated_sms: bool
    may_resolve_precise_location: bool   # True → H3 from live GPS; False → ZIP centroid only
    triage_dashboard_visible: bool       # always True — even Track B shows up
    outreach_channel: str                # "automated_sms" | "manual_phone_call"


def route_patient(consent: ConsentRecord) -> WorkflowPlan:
    """Translate a consent record into the workflow plan."""
    if consent.track is ConsentTrack.A_FULL:
        return WorkflowPlan(
            track=consent.track,
            may_ingest_device_telemetry=consent.telemetry_optin,
            may_send_automated_sms=consent.sms_optin,
            may_resolve_precise_location=consent.geo_optin,
            triage_dashboard_visible=True,
            outreach_channel="automated_sms" if consent.sms_optin else "manual_phone_call",
        )
    return WorkflowPlan(
        track=ConsentTrack.B_OPS,
        may_ingest_device_telemetry=False,
        may_send_automated_sms=False,
        may_resolve_precise_location=False,
        triage_dashboard_visible=True,
        outreach_channel="manual_phone_call",
    )


def fresh_track_a(patient_id: str, *, signed_at: datetime, policy_version: str) -> ConsentRecord:
    """Convenience builder — patient just signed the disclosure."""
    return ConsentRecord(
        patient_id=patient_id,
        track=ConsentTrack.A_FULL,
        signed_at=signed_at,
        privacy_policy_version=policy_version,
        telemetry_optin=True,
        sms_optin=True,
        geo_optin=True,
    )


def fresh_track_b(patient_id: str) -> ConsentRecord:
    """Convenience builder — patient declined / never installed app."""
    return ConsentRecord(
        patient_id=patient_id,
        track=ConsentTrack.B_OPS,
        signed_at=None,
        privacy_policy_version="N/A",
        telemetry_optin=False,
        sms_optin=False,
        geo_optin=False,
    )


if __name__ == "__main__":
    from datetime import timezone
    consented = fresh_track_a("PT-0001", signed_at=datetime.now(timezone.utc), policy_version="v3.2")
    declined = fresh_track_b("PT-0002")
    for c in (consented, declined):
        plan = route_patient(c)
        print(f"  {c.patient_id} track={plan.track.value:1s}  outreach={plan.outreach_channel:20s} "
              f"telemetry={plan.may_ingest_device_telemetry} sms={plan.may_send_automated_sms} "
              f"precise_geo={plan.may_resolve_precise_location}")
