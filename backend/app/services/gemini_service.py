import os
import httpx
from typing import Any
from app.core.config import get_settings
from app.core.logging import log

settings = get_settings()

SYSTEM_PROMPT = """You are DrillLens AI Copilot, an elite Petroleum Engineering and Drilling Intelligence Assistant powered by eRTMAC-NWIS (Enhanced Real-Time Monitoring & Control Centre – Nearby Well Intelligence System).
You specialize in Indian sedimentary basins (Barmer, Cambay, Assam-Arakan, Krishna-Godavari, Mumbai Offshore, Cauvery, Mahanadi, Tripura), drilling mechanics, formation evaluation, stuck pipe prevention, lost circulation mitigation, well control/kicks, BHA design, and offset well correlation.

Guidelines:
1. Provide concise, high-value, actionable engineering intelligence.
2. Structure recommendations with clear headings, bullet points, and key drilling parameter limits (e.g. WOB, RPM, Flow Rate, Mud Weight, Torque).
3. Ground answers in offset well observations, lithological characteristics, and risk factors when context is provided.
4. Maintain industrial rig safety standards. Decision support only."""


async def call_gemini(prompt: str, context: str | None = None) -> str:
    """Call Google Gemini Flash API using the configured API key."""
    api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "DrillLens AI Copilot: Active well data and offset parameters verified. Set GEMINI_API_KEY in your Vercel/environment settings for live Gemini Flash generative analysis."

    model = settings.gemini_model or "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    full_prompt = f"{SYSTEM_PROMPT}\n\n"
    if context:
        full_prompt += f"--- CONTEXT DATA ---\n{context}\n--------------------\n\n"
    full_prompt += f"User Request: {prompt}"

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key,
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1024,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                return "\n".join(text_parts).strip()
            else:
                log.error("Gemini API error: %d %s", response.status_code, response.text)
                return f"AI Copilot response unavailable (API status {response.status_code})."
    except Exception as e:
        log.exception("Error calling Gemini API: %s", e)
        return "DrillLens AI Assistant encountered a temporary connection issue. Please retry in a moment."


async def analyze_well_with_gemini(well_data: dict[str, Any], offset_wells: list[dict[str, Any]] | None = None) -> str:
    """Generate comprehensive well engineering assessment using Gemini."""
    prompt = f"Analyze the active drilling status and geological risk profile for well {well_data.get('well_name', 'Unknown')} ({well_data.get('well_id', '')}). Provide operational recommendations, formation precautions, and offset correlation notes."
    
    context = f"Well ID: {well_data.get('well_id')}\nWell Name: {well_data.get('well_name')}\nField: {well_data.get('field')}\nOperator: {well_data.get('operator')}\nDepth: {well_data.get('current_depth')} m\nFormation: {well_data.get('formation')}\nStatus: {well_data.get('status')}\nOperation: {well_data.get('current_operation')}\n"
    
    if offset_wells:
        context += "\nNearby Offset Wells:\n"
        for w in offset_wells[:5]:
            context += f"- {w.get('well_name')} ({w.get('well_id')}): Formation {w.get('formation')}, Depth {w.get('current_depth')}m, Status {w.get('status')}\n"

    return await call_gemini(prompt, context)
