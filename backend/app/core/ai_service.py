import httpx

# Your local Ollama endpoint (default port is 11434)
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5" # Change to "llama3.1" if you switch later

SYSTEM_PROMPT = """You are the SmartBiz AI, an expert Business Analyst, Stock Manager, and Growth Strategist for a retail shop in Nepal.

STRICT RULES:
1. Language: Answer in the language the user speaks (English or Nepali). If they use Roman Nepali, you can reply in Roman Nepali or Devanagari.
2. Accuracy: ONLY use the numbers provided in the 'LIVE DATABASE CONTEXT'. NEVER invent, guess, or hallucinate inventory numbers.
3. Tone: Professional, encouraging, and highly analytical.
4. Formatting: ALWAYS use Markdown. Use **bold** for item names, bullet points for lists, and emojis (📦, 🚨, 💰, 📈) to make the text beautiful on a mobile app.
5. Role: If asked for advice, analyze the provided data to suggest what to restock, how to clear dead stock, or how to increase profits."""

async def get_ai_advice(context_data: str, user_prompt: str) -> str:
    """Sends the context and prompt to the local Ollama instance."""
    
    full_prompt = f"LIVE DATABASE CONTEXT:\n{context_data}\n\nUSER QUESTION/INTENT:\n{user_prompt}"
    
    payload = {
        "model": MODEL_NAME,
        "system": SYSTEM_PROMPT,
        "prompt": full_prompt,
        "stream": False # Set to false so we get the whole message at once
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Timeout is 60 seconds because local LLMs can take a few seconds to think
            response = await client.post(OLLAMA_URL, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "Error generating response.")
        except httpx.ConnectError:
            return "⚠️ **Connection Error:** Could not reach the AI engine. Please ensure Ollama is running on your Mac (`ollama run qwen2.5`)."
        except Exception as e:
            return f"⚠️ **AI Error:** Something went wrong processing your request.\nDetails: {str(e)}"