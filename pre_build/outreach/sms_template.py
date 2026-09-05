"""
48-Hour Approve & Release SMS Templates (Spec §4 + §5 row 6 — *Ambient
Health-Weather Framing*).

The live MindStudio agent (spec §9.2) generates the polished, multilingual
SMS at the event. For pre-build we ship a deterministic, non-prescriptive
template fallback so:

  1. Outreach screens render real copy in the demo, and
  2. The pipeline still has a working SMS path if MindStudio is offline.

Style rules baked in (per spec):
  • Non-prescriptive — never tells the patient to change meds or dose.
  • Ambient framing — premium daily-weather utility, not a clinical alarm.
  • Behavioral nudge — one concrete recommended action.
  • ≤ 320 characters (2 SMS segments) to keep delivery costs flat.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmsContext:
    given_name: str
    head: str                       # respiratory | cardiovascular | metabolic
    climate_anomaly: str            # short phrase: "high ozone", "wildfire smoke", "heat wave"
    city: str
    horizon_hours: int = 48
    locale: str = "en"              # "en" | "es" | "hi" | "te"
    has_smart_home: bool = False


_NUDGE_BY_HEAD = {
    "respiratory": {
        "en": "Keeping windows closed and using an air purifier today gives your lungs the easiest ride.",
        "es": "Mantener las ventanas cerradas y usar un purificador de aire te ayudará a respirar más fácil.",
        "hi": "खिड़कियां बंद रखें और एयर प्यूरिफायर का उपयोग करें ताकि आपके फेफड़ों को राहत मिले।",
        "te": "కిటికీలు మూసివేసి ఎయిర్ ప్యూరిఫైయర్ ఉపయోగించడం వల్ల శ్వాస తీసుకోవడం సులభం అవుతుంది.",
    },
    "cardiovascular": {
        "en": "Drink water steadily and skip the midday outdoor walk — let your heart take it easy.",
        "es": "Bebe agua con frecuencia y evita caminar afuera al mediodía — dale un descanso a tu corazón.",
        "hi": "नियमित रूप से पानी पिएं और दोपहर में बाहर जाने से बचें — अपने दिल का ध्यान रखें।",
        "te": "క్రమం తప్పకుండా నీరు త్రాగండి మరియు మధ్యాహ్నం బయటకు వెళ్లడం మానుకోండి — గుండెకు విశ్రాంతి ఇవ్వండి.",
    },
    "metabolic": {
        "en": "Sip cool water often and snack on something light — your body works harder in this weather.",
        "es": "Toma agua fresca con frecuencia y come algo ligero — tu cuerpo se esfuerza más con este clima.",
        "hi": "ठंडा पानी पिएं और बैकअप पावर तैयार रखें — इस मौसम में आपके शरीर को अधिक देखभाल की जरूरत है।",
        "te": "చల్లని నీటిని తరచుగా త్రాగండి మరియు బ్యాకప్ పవర్ సిద్ధంగా ఉంచుకోండి — ఈ వాతావరణంలో జాగ్రత్త అవసరం.",
    },
}

_HEADERS = {
    "en": "Hi {name} — your VAYU Index just shifted because of {anomaly} near {city} over the next {hrs} hours.",
    "es": "Hola {name} — tu Índice VAYU cambió por {anomaly} cerca de {city} durante las próximas {hrs} horas.",
    "hi": "नमस्ते {name} — अगले {hrs} घंटों में {city} के पास {anomaly} के कारण आपका VAYU इंडेक्स बदल गया है।",
    "te": "నమస్కారం {name} — రాబోయే {hrs} గంటల్లో {city} సమీపంలో {anomaly} కారణంగా మీ VAYU సూచిక మారింది.",
}

_FOOTER = {
    "en": " Reply STOP to opt out.",
    "es": " Responde STOP para cancelar.",
    "hi": " सदस्यता समाप्त करने के लिए STOP भेजें।",
    "te": " నిలిపివేయడానికి STOP అని సమాధానం ఇవ్వండి.",
}


def render_sms(ctx: SmsContext) -> str:
    """Produce a ready-to-send, ≤320-char SMS string."""
    locale = ctx.locale if ctx.locale in ("en", "es", "hi", "te") else "en"
    if ctx.head not in _NUDGE_BY_HEAD:
        raise ValueError(f"unknown head '{ctx.head}'")
    header = _HEADERS[locale].format(
        name=ctx.given_name,
        anomaly=ctx.climate_anomaly,
        city=ctx.city,
        hrs=ctx.horizon_hours,
    )
    nudge = _NUDGE_BY_HEAD[ctx.head].get(locale, _NUDGE_BY_HEAD[ctx.head]["en"])
    footer = _FOOTER.get(locale, _FOOTER["en"])
    msg = f"{header} {nudge}{footer}"
    if len(msg) > 320:
        # Trim the nudge tail rather than the header — header carries patient context.
        excess = len(msg) - 320
        nudge = nudge[: max(0, len(nudge) - excess - 1)] + "…"
        msg = f"{header} {nudge}{footer}"
    return msg


if __name__ == "__main__":
    samples = [
        SmsContext(given_name="Maria", head="respiratory", climate_anomaly="high ozone",
                   city="Dallas", locale="es"),
        SmsContext(given_name="James", head="cardiovascular", climate_anomaly="a heat wave",
                   city="Fort Worth", locale="en"),
        SmsContext(given_name="Linda", head="metabolic", climate_anomaly="extreme humidity",
                   city="Houston", locale="en"),
    ]
    for s in samples:
        text = render_sms(s)
        print(f"  [{s.locale}] {len(text):3d} chars  | {text}")
