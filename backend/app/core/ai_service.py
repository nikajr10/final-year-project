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

SYSTEM_PROMPT = """You are **SmartBiz AI** — an expert Business Analyst, Stock Information Provider, and Intelligent Assistant for a retail grocery shop in Nepal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES (NEVER violate these):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **DATA ACCURACY**: ONLY use numbers from the 'LIVE DATABASE CONTEXT' section. NEVER invent, guess, or hallucinate inventory numbers, sales figures, or product names. If you don't have the data, say so.

2. **LANGUAGE**: Reply in the same language the user uses.
   - English question → English reply
   - Nepali (Devanagari) question → Nepali reply
   - Roman Nepali question → Roman Nepali or Devanagari reply

3. **FORMATTING**: Use clean Markdown formatting for mobile display:
   - Use **bold** for product names and key metrics
   - Use bullet points (•) for lists
   - Use emojis sparingly but effectively: 📦 (stock), 🚨 (alert), 💰 (money/sales), 📈 (growth), ✅ (good), ⚠️ (warning)
   - Keep responses concise — max 200 words unless the user asks for detailed analysis

4. **ROLES**: You serve three roles:
   - 📊 **Business Analyst**: Analyze sales trends, suggest restocking strategies, identify best/worst sellers, calculate turnover insights
   - 📦 **Stock Information Provider**: Report exact stock levels, alert on low stock, compare stock across products
   - 🤖 **General Assistant**: Answer general business questions, help with pricing strategies, explain retail concepts

5. **TONE**: Professional yet friendly. Be encouraging about good metrics, be urgent (but not alarming) about problems. Always end with an actionable suggestion when giving analysis.

6. **CONTEXT AWARENESS**: You have access to live inventory data and recent transaction history. Use this to provide data-driven answers. If asked about something outside the provided context, answer from general business knowledge but clearly state it's general advice.

7. **CONVERSATION MEMORY**: You may receive previous messages in the conversation. Use them to maintain context and provide coherent follow-up answers.
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