"""
ai_service.py
=============
SmartBiz AI — Chatbot Brain powered by local Ollama (Qwen 2.5 7B).
No internet required, no API key needed. Runs fully offline.

Responsibilities:
  1. Receive structured context (inventory snapshot, sales data, etc.)
  2. Receive the user's question or a system-generated intent
  3. Build a rich prompt with system instructions + context + conversation history
  4. Call Ollama and return the AI's reply
"""

import httpx

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"  # Qwen 2.5 7B — user's chosen model

# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — defines the AI's personality and rules
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are **SmartBiz AI** — a professional Business Analyst and Inventory Advisor for a retail grocery shop in Nepal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES (NEVER violate these):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **DATA ACCURACY**: Use ONLY figures from the 'LIVE DATABASE CONTEXT' section. Never fabricate inventory quantities, revenue figures, or product names. If data is unavailable, politely state so.

2. **LANGUAGE**: Always reply in the same language the user writes in.
   - English → English reply
   - Nepali (Devanagari) → Nepali reply
   - Roman Nepali → Roman Nepali or Devanagari reply

3. **TONE & STYLE**:
   - Be professional, polite, and concise — speak like a trusted business advisor
   - Use clear business terminology: revenue, gross margin, stockout risk, turnover rate, reorder point, net profit, cost of goods sold (COGS), etc.
   - Keep responses under 200 words unless a detailed analysis is requested
   - Never be blunt or harsh — always frame concerns respectfully

4. **FORMATTING RULES**:
   - Begin with a brief 1–2 sentence professional summary
   - List all important details using bullet points (•) — never bury key data in paragraphs
   - Use **bold** for product names, figures, and key business terms
   - Use emojis purposefully: 📦 stock · 🚨 critical alert · 💰 revenue · 📈 growth · ✅ healthy · ⚠️ caution
   - **Profit figures → prefix with 🟢** (e.g., 🟢 Net Profit: Rs. 4,200)
   - **Loss figures → prefix with 🔴** (e.g., 🔴 Net Loss: Rs. 1,500)
   - Always close with a short, actionable **💡 Suggestion:** on a new line

5. **ROLES**:
   - 📊 **Business Analyst**: Identify sales trends, top/low performers, margin analysis, and reorder recommendations
   - 📦 **Inventory Advisor**: Report precise stock levels, flag stockout risks, and highlight dead stock
   - 🤖 **General Advisor**: Offer pricing strategy, retail best practices, and general business guidance — clearly marking any general advice as such

6. **CONTEXT AWARENESS**: Ground every response in the live data provided. For questions outside the available data, draw on general retail knowledge and explicitly note it as general advice.

7. **CONVERSATION MEMORY**: Maintain coherence across the conversation by referencing prior messages when relevant.
"""


# ══════════════════════════════════════════════════════════════════════════════
# MAIN AI FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

async def get_ai_advice(
    context_data: str,
    user_prompt: str,
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Send context + prompt to local Ollama and return the AI's reply.

    Parameters
    ----------
    context_data : str
        Structured data from the database (inventory, sales, etc.)
    user_prompt : str
        The user's actual question or a system-generated intent string
    conversation_history : list[dict] | None
        Previous messages in the conversation for multi-turn context.
        Each dict has keys: 'role' ('user' | 'ai') and 'text'.

    Returns
    -------
    str
        The AI's response text, or an error message if something fails.
    """

    # ── Build conversation context ────────────────────────────────────────────
    history_block = ""
    if conversation_history:
        # Include up to last 6 messages for context (to stay within token limits)
        recent = conversation_history[-6:]
        history_lines = []
        for msg in recent:
            role_label = "User" if msg.get("role") == "user" else "SmartBiz AI"
            history_lines.append(f"{role_label}: {msg.get('text', '')}")
        history_block = "\n\nPREVIOUS CONVERSATION:\n" + "\n".join(history_lines)

    # ── Build full prompt ─────────────────────────────────────────────────────
    full_prompt = (
        f"LIVE DATABASE CONTEXT:\n{context_data}"
        f"{history_block}"
        f"\n\nUSER QUESTION/INTENT:\n{user_prompt}"
    )

    payload = {
        "model": MODEL_NAME,
        "system": SYSTEM_PROMPT,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,       # Low temp for factual accuracy
            "num_predict": 512,       # Max tokens — keeps responses concise
            "top_p": 0.9,
        },
    }

    async with httpx.AsyncClient() as client:
        try:
            # Timeout is 120s because local 7B models on CPU can take time
            response = await client.post(OLLAMA_URL, json=payload, timeout=120.0)
            response.raise_for_status()
            data = response.json()
            reply = data.get("response", "").strip()

            if not reply:
                return "⚠️ The AI returned an empty response. Please try again."

            return reply

        except httpx.ConnectError:
            return (
                "⚠️ **Connection Error:** Could not reach the AI engine.\n\n"
                "Please ensure Ollama is running:\n"
                "```\nollama run qwen2.5:7b\n```"
            )
        except httpx.ReadTimeout:
            return (
                "⏳ **Timeout:** The AI took too long to respond.\n\n"
                "This can happen with complex questions. Please try:\n"
                "• Asking a simpler question\n"
                "• Checking if Ollama is under heavy load"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return (
                    f"⚠️ **Model Not Found:** The model `{MODEL_NAME}` is not installed.\n\n"
                    f"Please open a terminal and run:\n"
                    f"`ollama pull {MODEL_NAME}`"
                )
            return f"⚠️ **AI Error:** Server returned status {e.response.status_code}."
        except Exception as e:
            return f"⚠️ **AI Error:** {str(e)}"