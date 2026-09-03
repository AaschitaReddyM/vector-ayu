import os
from pathlib import Path
from google import genai
from pre_build.outreach.sms_template import SmsContext, render_sms

def generate_sms(ctx: SmsContext) -> str:
    """
    Uses Google Cloud Vertex AI (Gemini) to generate a personalized, bilingual SMS nudge.
    Falls back to deterministic templates on error.
    """
    key_path = Path(r"c:\Users\Vector-Ayu (VAYU)\Desktop\vayu\version-1\gcp-key.json.json")
    
    if not key_path.exists():
        print("  [Agent] gcp-key.json.json not found. Using deterministic fallback template.")
        return render_sms(ctx)

    # Point the Google SDK to our existing GCP service account key
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path)

    try:
        # Connect natively to Google Cloud Vertex AI instead of AI Studio
        client = genai.Client(
            vertexai=True,
            project="vayu-patchamomma-2026",
            location="us-central1"
        )
        
        language = "Spanish" if ctx.locale == "es" else "English"
        
        prompt = f"""
        You are the VAYU AI Triage Agent. Your job is to draft a personalized, 
        ambient health-weather SMS nudge for a high-risk patient.

        Patient Details:
        - Name: {ctx.given_name}
        - Primary Vulnerability: {ctx.head.title()}
        - Approaching Climate Anomaly: {ctx.climate_anomaly} near {ctx.city}
        - Language: {language}
        
        Rules:
        1. Output strictly the SMS text, nothing else. No markdown, no quotes.
        2. Write in {language}.
        3. Keep it under 300 characters.
        4. Ambient framing — frame it as a premium weather utility, not a clinical alarm.
        5. Non-prescriptive — never provide medical diagnoses or tell them to change medication or dose.
        6. Provide exactly one actionable, non-prescriptive behavioral nudge (e.g. keep windows closed, drink water).
        7. Append exactly this text at the very end: " Reply STOP to opt out." (or " Responde STOP para cancelar." if Spanish).
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        msg = response.text.strip()
        
        if len(msg) > 320:
            msg = msg[:317] + "..."
            
        print("  [Agent] Successfully drafted personalized SMS via Vertex AI.")
        return msg
        
    except Exception as e:
        print(f"  [Agent] Vertex AI error: {e}. Falling back to template.")
        return render_sms(ctx)
