import os
from pathlib import Path
from google import genai
from pre_build.outreach.sms_template import SmsContext, render_sms

def generate_sms(ctx: SmsContext) -> str:
    """
    Uses Google Cloud Vertex AI (Gemini) to generate a personalized, bilingual SMS nudge.
    Falls back to deterministic templates on error.
    """
    key_path = Path(__file__).resolve().parent.parent.parent / "gcp-key.json.json"
    if not key_path.exists():
        key_path = Path(r"c:\Users\Vector-Ayu (VAYU)\Desktop\vayu\version-1\gcp-key.json.json")
    
    if key_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path)

    try:
        # Connect natively to Google Cloud Vertex AI instead of AI Studio
        client = genai.Client(
            vertexai=True,
            project="vayu-patchamomma-2026",
            location="us-central1"
        )
        
        language_map = {
            "en": "English",
            "es": "Spanish",
            "hi": "Hindi",
            "te": "Telugu"
        }
        
        target_language = language_map.get(ctx.locale, "English")
        
        opt_out_instruction = 'Append exactly this text at the very end in English: " Reply STOP to opt out."'
        if ctx.locale == "es": opt_out_instruction = 'Append exactly this text at the very end: " Responde STOP para cancelar."'
            
        nest_instruction = ""
        if ctx.has_smart_home:
            if ctx.head == "respiratory":
                if ctx.city == "New Delhi":
                    nest_instruction = "Crucial: Briefly mention their Xiaomi Smart Air Purifier is now on turbo mode."
                else:
                    nest_instruction = "Crucial: Briefly mention their Google Nest HVAC fan is now filtering their air."
            elif ctx.head == "cardiovascular":
                if ctx.city == "New Delhi":
                    nest_instruction = "Crucial: Briefly mention their Tata Smart AC is pre-cooling the home to 22C."
                else:
                    nest_instruction = "Crucial: Briefly mention their Google Nest is pre-cooling the home to 68F."
            elif ctx.head == "metabolic":
                if ctx.city == "New Delhi":
                    nest_instruction = "Crucial: Briefly mention their Luminous Smart Inverter is reserving 100% battery."
                else:
                    nest_instruction = "Crucial: Briefly mention their Tesla Powerwall has activated storm watch."
            nest_instruction = "9. " + nest_instruction
        prompt = f"""
        You are the VAYU AI Triage Agent. Your job is to draft a personalized, 
        ambient health-weather SMS nudge for a high-risk patient.

        Patient Details:
        - Name: {ctx.given_name}
        - Primary Vulnerability: {ctx.head.title()}
        - Approaching Climate Anomaly: {ctx.climate_anomaly} near {ctx.city}
        - Has Smart Home: {ctx.has_smart_home}
        
        Rules:
        1. Output strictly the SMS text, nothing else. No markdown, no quotes.
        2. Write the message entirely in {target_language}.
        3. Keep the total length under 300 characters if possible.
        4. Always start the first message with "Hi/Hola/Namaste {ctx.given_name},".
        5. Ambient framing — frame it as a premium weather utility, not a clinical alarm.
        6. Non-prescriptive — never provide medical diagnoses or tell them to change medication or dose.
        7. Provide exactly one actionable, non-prescriptive behavioral nudge (e.g. keep windows closed, drink water).
        8. {opt_out_instruction}
        {nest_instruction}
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
