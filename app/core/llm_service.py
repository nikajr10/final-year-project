"""
llm_service.py
==============
Nepali Voice Inventory Management System — LLM Brain
Uses local Ollama (llama3) — no internet, no API key needed.

Flow
----
whisper_service.py  →  cleaned token string
                    →  LLMService.process_text()
                    →  { intent, item, qty, unit }

Design
------
1. Regex parser runs FIRST — instant, free, 100% deterministic.
2. Ollama/Llama3 only called when regex is not confident.
3. Two-agent pipeline preserved (CoT translator → JSON extractor)
   but with a MUCH stronger prompt so Llama3 cannot hallucinate.
"""

import re
import json
import requests


# ══════════════════════════════════════════════════════════════════════════════
# CANONICAL REFERENCE  (single source of truth — mirror in whisper_service.py)
# ══════════════════════════════════════════════════════════════════════════════

# English canonical name  →  Nepali display name (used in JSON output)
ITEM_MAP = {
    "Rice":        "Chamal",
    "Lentils":     "Daal",
    "Salt":        "Nun",
    "Sugar":       "Chini",
    "Oil":         "Tel",
    "Flour":       "Maida",
    "Turmeric":    "Besar",
    "Eggs":        "Anda",
    "Beaten_Rice": "Chiura",
    "Biscuits":    "Biskut",
}

# What unit to assume if the speaker did not mention one
DEFAULT_UNIT = {
    "Rice":        "kg",
    "Lentils":     "kg",
    "Salt":        "kg",
    "Sugar":       "kg",
    "Oil":         "liter",
    "Flour":       "kg",
    "Turmeric":    "kg",
    "Eggs":        "pieces",
    "Beaten_Rice": "kg",
    "Biscuits":    "packet",
}

# All surface forms the whisper cleaner may output → canonical English item
ITEM_ALIASES = {
    # Rice
    "rice": "Rice", "chamal": "Rice", "chaamal": "Rice",
    # Lentils
    "lentils": "Lentils", "lentil": "Lentils",
    "daal": "Lentils", "dal": "Lentils", "dhal": "Lentils",
    # Salt
    "salt": "Salt", "nun": "Salt",
    # Sugar
    "sugar": "Sugar", "chini": "Sugar", "sini": "Sugar",
    # Oil
    "oil": "Oil", "tel": "Oil",
    # Flour
    "flour": "Flour", "maida": "Flour",
    # Turmeric
    "turmeric": "Turmeric", "besar": "Turmeric", "haldi": "Turmeric",
    # Eggs
    "eggs": "Eggs", "egg": "Eggs", "anda": "Eggs",
    # Beaten Rice
    "beaten_rice": "Beaten_Rice", "beaten rice": "Beaten_Rice",
    "chiura": "Beaten_Rice", "chiuraa": "Beaten_Rice",
    # Biscuits
    "biscuits": "Biscuits", "biscuit": "Biscuits",
    "biskut": "Biscuits", "biscut": "Biscuits",
}

# All surface forms → canonical action string
ACTION_ALIASES = {
    # Add
    "add": "ADD", "thap": "ADD", "aayo": "ADD", "rakh": "ADD",
    "kinyo": "ADD", "increase": "ADD",
    # Remove
    "remove": "REMOVE", "ghata": "REMOVE", "ghatau": "REMOVE",
    "bech": "REMOVE", "hatau": "REMOVE", "sell": "REMOVE",
    "sold": "REMOVE", "decrease": "REMOVE",
    # Check
    "check": "CHECK", "kati": "CHECK", "banki": "CHECK",
    "baaki": "CHECK", "stock": "CHECK",
}

# All surface forms → canonical unit string
UNIT_ALIASES = {
    "kg": "kg", "kilo": "kg", "kilogram": "kg", "kilograms": "kg",
    "pieces": "pieces", "piece": "pieces", "wata": "pieces", "ota": "pieces",
    "packet": "packet", "packets": "packet",
    "liter": "liter", "litre": "liter", "liters": "liter", "litres": "liter",
}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

# Reverse map: Nepali display name → English canonical (for _validate_json)
NEPALI_TO_EN = {v: k for k, v in ITEM_MAP.items()}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 PROMPT — Chain-of-Thought Translator
# ══════════════════════════════════════════════════════════════════════════════

AGENT1_PROMPT_TEMPLATE = """
You are a strict inventory command translator for a Nepali grocery store.
The input is a pre-processed speech-to-text string that may contain a mix of
English tokens, Romanized Nepali, or Devanagari script.

YOUR ONLY JOB: Follow the 5 steps below and output ONE clean English sentence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — FIND THE ITEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
There are EXACTLY 10 valid items. Map any variant to the canonical name:

  Rice        <- chamal, chaamal, ryce, samal
  Lentils     <- daal, dal, dhal
  Salt        <- nun, noon
  Sugar       <- chini, sini, cheeni
  Oil         <- tel, tail
  Flour       <- maida
  Turmeric    <- besar, besaar, haldi
  Eggs        <- anda, undo, egg
  Beaten_Rice <- chiura  (ALWAYS write as "Beaten_Rice" with underscore)
  Biscuits    <- biskut, biscuit

  If you cannot identify the item, write "UNKNOWN_ITEM"

STEP 2 — FIND THE QUANTITY
  Look for digits (5, 10) or number words (five, ten).
  If no quantity is spoken and action is Add or Remove, assume 1.
  If action is Check, quantity is 0.

STEP 3 — FIND THE UNIT
  Valid units: kg | pieces | packet | liter
  If no unit is spoken, use the default for the item:
    Rice->kg  Lentils->kg  Salt->kg  Sugar->kg  Oil->liter
    Flour->kg  Turmeric->kg  Eggs->pieces  Beaten_Rice->kg  Biscuits->packet

STEP 4 — FIND THE ACTION
  Add     <- add, thap, aayo, rakh, kinyo, bought, received, increase
  Remove  <- remove, ghata, ghatau, bech, hatau, sold, used, decrease
  Check   <- check, kati, banki, baaki, how much, how many, stock
  If unclear, write "UNKNOWN_ACTION"

STEP 5 — WRITE THE FINAL TRANSLATION
  Format MUST be exactly: <Action> <Quantity> <Unit> <Item>
  The last line of your response MUST start with "Translation:"

EXAMPLES:
  Input: "Turmeric 5 kg Remove"
  Thought: Item=Turmeric, Qty=5, Unit=kg, Action=Remove
  Translation: Remove 5 kg Turmeric

  Input: "Add 10 pieces Eggs"
  Thought: Item=Eggs, Qty=10, Unit=pieces, Action=Add
  Translation: Add 10 pieces Eggs

  Input: "Check Rice"
  Thought: Item=Rice, Qty=0, Unit=kg, Action=Check
  Translation: Check 0 kg Rice

  Input: "chiura 3 kg thap"
  Thought: chiura=Beaten_Rice, Qty=3, Unit=kg, thap=Add
  Translation: Add 3 kg Beaten_Rice

  Input: "Besar 5 kg ghata"
  Thought: Besar=Turmeric, Qty=5, Unit=kg, ghata=Remove
  Translation: Remove 5 kg Turmeric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Now analyze this input:

Input: '{text}'
Thought Process:
"""


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 PROMPT — Strict JSON Extractor
# ══════════════════════════════════════════════════════════════════════════════

AGENT2_PROMPT_TEMPLATE = """
You are a strict JSON extraction engine. Convert the English inventory command
into a JSON object. Return ONLY the JSON — no explanation, no markdown, no extra text.

VALID VALUES:
  intent : "ADD" | "REMOVE" | "CHECK"
  item   : EXACTLY one of → "Chamal" "Daal" "Nun" "Chini" "Tel"
                             "Maida" "Besar" "Anda" "Chiura" "Biskut"
  qty    : integer >= 0   (must be 0 for CHECK)
  unit   : "kg" | "pieces" | "packet" | "liter"

ITEM MAPPING (English canonical → output value):
  Rice        -> "Chamal"
  Lentils     -> "Daal"
  Salt        -> "Nun"
  Sugar       -> "Chini"
  Oil         -> "Tel"
  Flour       -> "Maida"
  Turmeric    -> "Besar"
  Eggs        -> "Anda"
  Beaten_Rice -> "Chiura"
  Biscuits    -> "Biskut"

RULES:
  - qty must be an integer (never null, never a string, never a float)
  - CHECK intent forces qty to 0
  - item must be one of the 10 values above — never anything else

Command: '{command}'
JSON:
"""


# ══════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC REGEX PARSER  (runs before Ollama — instant & zero cost)
# ══════════════════════════════════════════════════════════════════════════════

def _regex_parse(text: str) -> dict | None:
    """
    Try to extract all 4 fields using pure pattern matching.
    Returns a complete result dict on success, or None to fall through to LLM.
    """
    t = text.lower().strip()

    # ── Action ────────────────────────────────────────────────────────────────
    action = None
    for alias, canonical in ACTION_ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', t):
            action = canonical
            break
    if action is None:
        return None

    # ── Item ──────────────────────────────────────────────────────────────────
    item_en = None
    if re.search(r'beaten[_ ]rice', t):           # two-word form first
        item_en = "Beaten_Rice"
    else:
        for alias, canonical in ITEM_ALIASES.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', t):
                item_en = canonical
                break
    if item_en is None:
        return None

    # ── Quantity ──────────────────────────────────────────────────────────────
    qty = 0
    if action in ("ADD", "REMOVE"):
        m = re.search(r'\b(\d+)\b', t)
        if m:
            qty = int(m.group(1))
        else:
            for word, val in NUMBER_WORDS.items():
                if re.search(r'\b' + word + r'\b', t):
                    qty = val
                    break
            if qty == 0:
                qty = 1                            # implied single unit

    # ── Unit ──────────────────────────────────────────────────────────────────
    unit = None
    for alias, canonical in UNIT_ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', t):
            unit = canonical
            break
    if unit is None:
        unit = DEFAULT_UNIT.get(item_en, "kg")

    # ── Convert to Nepali display name ────────────────────────────────────────
    item_nepali = ITEM_MAP.get(item_en, item_en)

    return {
        "intent": action,
        "item":   item_nepali,
        "qty":    float(qty),
        "unit":   unit,
    }


# ══════════════════════════════════════════════════════════════════════════════
# LLM SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class LLMService:
    def __init__(self):
        self.api_url     = "http://localhost:11434/api/generate"
        self.model       = "llama3"
        self.valid_items = list(ITEM_MAP.values())   # Nepali display names

    # ──────────────────────────────────────────────────────────────────────────
    def _call_ollama(self, prompt: str, format_json: bool = False) -> str:
        payload = {
            "model":  self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0},
        }
        if format_json:
            payload["format"] = "json"

        response = requests.post(self.api_url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "").strip()

    # ──────────────────────────────────────────────────────────────────────────
    def _validate_json(self, data: dict) -> dict:
        """
        Sanitise Llama3's JSON so it always meets the contract,
        even if the model drifts slightly from instructions.
        """
        # Intent
        intent = str(data.get("intent", "")).upper()
        if intent not in ("ADD", "REMOVE", "CHECK"):
            intent = "ADD"

        # Item — accept both Nepali display name and English canonical
        item_raw = str(data.get("item", "")).strip()
        if item_raw in self.valid_items:
            item = item_raw
        else:
            # Try English canonical → convert to Nepali
            item_en = item_raw.replace(" ", "_").title()
            item = ITEM_MAP.get(item_en)
            if item is None:
                # Last resort: fuzzy match against Nepali names
                item_lower = item_raw.lower()
                item = next(
                    (v for v in self.valid_items if v.lower() == item_lower),
                    "Chamal"     # absolute fallback — better than crashing
                )

        # Quantity
        try:
            qty = float(data.get("qty", 0))
            if qty < 0:
                qty = 0.0
        except (ValueError, TypeError):
            qty = 0.0

        if intent == "CHECK":
            qty = 0.0

        # Unit
        unit = str(data.get("unit", "")).lower().strip()
        if unit not in ("kg", "pieces", "packet", "liter"):
            item_en_lookup = NEPALI_TO_EN.get(item, "Rice")
            unit = DEFAULT_UNIT.get(item_en_lookup, "kg")

        return {"intent": intent, "item": item, "qty": qty, "unit": unit}

    # ──────────────────────────────────────────────────────────────────────────
    def process_text(self, text: str) -> dict | None:
        """
        Main entry point. Returns:
          { "intent": ADD|REMOVE|CHECK,
            "item":   Nepali display name,
            "qty":    float,
            "unit":   kg|pieces|packet|liter }
        or None on total failure.
        """
        print(f"\n🧠 [Agent 1] Analyzing Cleaned Audio Context: '{text}'")

        # ── 1. Regex fast path ────────────────────────────────────────────────
        regex_result = _regex_parse(text)
        if regex_result:
            print(f"⚡ Regex parser: {regex_result}")
            return regex_result

        # ── 2. Ollama two-agent pipeline ──────────────────────────────────────
        print("🤖 Regex inconclusive — calling Llama3...")

        try:
            # AGENT 1 — Chain-of-thought translator
            a1_prompt    = AGENT1_PROMPT_TEMPLATE.format(text=text)
            cot_response = self._call_ollama(a1_prompt, format_json=False)
            print(f"   ↳ AI Internal Logic:\n{cot_response}")

            # Extract the "Translation:" line
            clean_english = ""
            for line in cot_response.split("\n"):
                if line.strip().lower().startswith("translation:"):
                    clean_english = line.split(":", 1)[1].strip()
                    break

            # Fallback: use last non-empty line
            if not clean_english:
                lines = [l.strip() for l in cot_response.split("\n") if l.strip()]
                clean_english = lines[-1] if lines else text

            print(f"   ↳ Final Translated Meaning: '{clean_english}'")

            # Try regex again on the now-clean English before hitting Agent 2
            regex_on_clean = _regex_parse(clean_english)
            if regex_on_clean:
                print(f"⚡ Regex on clean English: {regex_on_clean}")
                return regex_on_clean

            # AGENT 2 — Strict JSON extractor
            print("🧠 [Agent 2] Extracting JSON Data...")
            a2_prompt = AGENT2_PROMPT_TEMPLATE.format(command=clean_english)
            json_str  = self._call_ollama(a2_prompt, format_json=True)
            print(f"   ↳ Raw JSON from Llama3: {json_str!r}")

            raw_data  = json.loads(json_str)
            validated = self._validate_json(raw_data)
            print(f"   ↳ Final Extracted JSON: {validated}")
            return validated

        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            return None
        except requests.RequestException as e:
            print(f"❌ Ollama connection error — is Ollama running? ({e})")
            return None
        except Exception as e:
            print(f"❌ LLM Pipeline Error: {e}")
            return None