"""
llm_service.py
==============
Nepali Voice Inventory — LLM Brain

Biscuit routing:
  "Tiger Biscuit"    → item: "Tiger Biskut"    (Nepali display)
  "Digestive Biscuit"→ item: "Digestive Biskut"(Nepali display)
  "Biscuit" alone    → item: "Digestive Biskut"(default)
"""

import re
import json
import requests


# ══════════════════════════════════════════════════════════════════════════════
# CANONICAL MAPS
# ══════════════════════════════════════════════════════════════════════════════

ITEM_MAP = {
    "Rice":             "Chamal",
    "Lentils":          "Daal",
    "Salt":             "Nun",
    "Sugar":            "Chini",
    "Oil":              "Tel",
    "Flour":            "Maida",
    "Turmeric":         "Besar",
    "Eggs":             "Anda",
    "Beaten_Rice":      "Chiura",
    "Biscuits":         "Digestive Biskut",   # generic biscuit → digestive
    "Digestive Biscuit":"Digestive Biskut",
    "Tiger Biscuit":    "Tiger Biskut",
}

DEFAULT_UNIT = {
    "Rice":             "kg",
    "Lentils":          "kg",
    "Salt":             "kg",
    "Sugar":            "kg",
    "Oil":              "liter",
    "Flour":            "kg",
    "Turmeric":         "kg",
    "Eggs":             "pieces",
    "Beaten_Rice":      "kg",
    "Biscuits":         "packet",
    "Digestive Biscuit":"packet",
    "Tiger Biscuit":    "packet",
}

# Surface forms → English canonical
# IMPORTANT: multi-word entries MUST come before single-word entries
# The regex parser checks longest patterns first via sorted() below.
ITEM_ALIASES = {
    # ── Tiger Biscuit variants (check before generic "biscuit") ───────────────
    "tiger biscuit":      "Tiger Biscuit",
    "tiger biscuits":     "Tiger Biscuit",
    "tiger biskut":       "Tiger Biscuit",
    "tiger biskutt":      "Tiger Biscuit",
    "tiger biscut":       "Tiger Biscuit",
    "taiger biscuit":     "Tiger Biscuit",
    "taiger biskut":      "Tiger Biscuit",
    "tigger biscuit":     "Tiger Biscuit",
    "tiger biskut":       "Tiger Biscuit",

    # ── Digestive Biscuit variants (check before generic "biscuit") ───────────
    "digestive biscuit":  "Digestive Biscuit",
    "digestive biscuits": "Digestive Biscuit",
    "digestive biskut":   "Digestive Biscuit",
    "digestive biskutt":  "Digestive Biscuit",
    "digestive biscut":   "Digestive Biscuit",
    "dajestiv biscuit":   "Digestive Biscuit",
    "daigestive biscuit": "Digestive Biscuit",

    # ── Generic biscuit → default to Digestive ────────────────────────────────
    "biscuits":           "Digestive Biscuit",
    "biscuit":            "Digestive Biscuit",
    "biskut":             "Digestive Biscuit",
    "biscut":             "Digestive Biscuit",
    "biskutt":            "Digestive Biscuit",

    # ── Rice ──────────────────────────────────────────────────────────────────
    "rice": "Rice", "chamal": "Rice", "chaamal": "Rice",

    # ── Lentils ───────────────────────────────────────────────────────────────
    "lentils": "Lentils", "lentil": "Lentils",
    "daal": "Lentils", "dal": "Lentils", "dhal": "Lentils",

    # ── Salt ──────────────────────────────────────────────────────────────────
    "salt": "Salt", "nun": "Salt",

    # ── Sugar ─────────────────────────────────────────────────────────────────
    "sugar": "Sugar", "chini": "Sugar", "sini": "Sugar",

    # ── Oil ───────────────────────────────────────────────────────────────────
    "oil": "Oil", "tel": "Oil",

    # ── Flour ─────────────────────────────────────────────────────────────────
    "flour": "Flour", "maida": "Flour",

    # ── Turmeric ──────────────────────────────────────────────────────────────
    "turmeric": "Turmeric", "besar": "Turmeric", "haldi": "Turmeric",

    # ── Eggs ──────────────────────────────────────────────────────────────────
    "eggs": "Eggs", "egg": "Eggs", "anda": "Eggs",

    # ── Beaten Rice ───────────────────────────────────────────────────────────
    "beaten_rice": "Beaten_Rice", "beaten rice": "Beaten_Rice",
    "chiura": "Beaten_Rice", "chiuraa": "Beaten_Rice",
}

ACTION_ALIASES = {
    "add": "ADD", "increase": "ADD", "bought": "ADD",
    "badhau": "ADD", "badhaau": "ADD", "badhayo": "ADD",
    "badha": "ADD", "badhyo": "ADD",
    "thap": "ADD", "thapaau": "ADD", "thapyo": "ADD",
    "kinyo": "ADD", "rakh": "ADD", "aayo": "ADD",

    "remove": "REMOVE", "sell": "REMOVE", "sold": "REMOVE",
    "decrease": "REMOVE", "reduce": "REMOVE",
    "ghatau": "REMOVE", "ghataau": "REMOVE", "ghata": "REMOVE",
    "ghatayo": "REMOVE",
    "bech": "REMOVE", "bechyo": "REMOVE",
    "hatau": "REMOVE", "hatayo": "REMOVE",
    "nikal": "REMOVE", "kharch": "REMOVE",
    "bikyo": "REMOVE",

    "check": "CHECK", "stock": "CHECK",
    "kati": "CHECK", "banki": "CHECK", "baaki": "CHECK", "baki": "CHECK",
}

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

NEPALI_TO_EN = {v: k for k, v in ITEM_MAP.items()}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

AGENT1_PROMPT_TEMPLATE = """
You are a strict inventory command translator for a Nepali grocery store.
The input is a pre-processed speech-to-text string.

YOUR ONLY JOB: Follow the 5 steps below and output ONE clean English sentence.

STEP 1 — FIND THE ITEM
  Valid items (map any variant to exact canonical name):
  Rice, Lentils, Salt, Sugar, Oil, Flour, Turmeric, Eggs, Beaten_Rice,
  Tiger Biscuit, Digestive Biscuit

  BISCUIT RULES (critical):
    "tiger biscuit" / "tiger biskut"       → Tiger Biscuit
    "digestive biscuit" / "digestive biskut" → Digestive Biscuit
    "biscuit" / "biskut" alone (no variant) → Digestive Biscuit
  If you cannot identify the item, write "UNKNOWN_ITEM"

STEP 2 — FIND THE QUANTITY
  Look for digits or number words. Default 1 for Add/Remove, 0 for Check.

STEP 3 — FIND THE UNIT
  Valid: kg | pieces | packet | liter
  Defaults: Rice->kg  Lentils->kg  Salt->kg  Sugar->kg  Oil->liter
            Flour->kg  Turmeric->kg  Eggs->pieces  Beaten_Rice->kg
            Tiger Biscuit->packet  Digestive Biscuit->packet

STEP 4 — FIND THE ACTION
  Add    <- badhau, thap, kinyo, rakh, aayo, bought, increase
  Remove <- ghatau, ghata, bech, hatau, nikal, sold, decrease
  Check  <- check, kati, banki, baaki, how much, stock

STEP 5 — WRITE THE TRANSLATION
  Format: <Action> <Quantity> <Unit> <Item>
  Last line MUST start with "Translation:"

EXAMPLES:
  Input: "10 packet Tiger Biscuit Add"
  Translation: Add 10 packet Tiger Biscuit

  Input: "5 packet Digestive Biscuit Remove"
  Translation: Remove 5 packet Digestive Biscuit

  Input: "10 packet Biscuits Add"
  Translation: Add 10 packet Digestive Biscuit

Now analyze: '{text}'
Thought Process:
"""

AGENT2_PROMPT_TEMPLATE = """
You are a strict JSON extraction engine.
Return ONLY valid JSON — no explanation, no markdown.

VALID VALUES:
  intent : "ADD" | "REMOVE" | "CHECK"
  item   : EXACTLY one of ->
           "Chamal" "Daal" "Nun" "Chini" "Tel" "Maida" "Besar"
           "Anda" "Chiura" "Tiger Biskut" "Digestive Biskut"
  qty    : integer >= 0
  unit   : "kg" | "pieces" | "packet" | "liter"

BISCUIT RULES:
  Tiger Biscuit    -> "Tiger Biskut"
  Digestive Biscuit-> "Digestive Biskut"
  Biscuit (generic)-> "Digestive Biskut"

Command: '{command}'
JSON:
"""


# ══════════════════════════════════════════════════════════════════════════════
# REGEX PARSER
# ══════════════════════════════════════════════════════════════════════════════

def _regex_parse(text: str) -> dict | None:
    t = text.lower().strip()

    # ── Action ────────────────────────────────────────────────────────────────
    action = None
    for alias, canonical in ACTION_ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', t):
            action = canonical
            break
    if action is None:
        return None

    # ── Item — LONGEST MATCH FIRST so "tiger biscuit" beats "biscuit" ─────────
    item_en = None
    for alias in sorted(ITEM_ALIASES.keys(), key=len, reverse=True):
        pattern = re.escape(alias).replace(r"\ ", r"\s+")
        if re.search(r'\b' + pattern + r'\b', t):
            item_en = ITEM_ALIASES[alias]
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
                qty = 1

    # ── Unit ──────────────────────────────────────────────────────────────────
    unit = None
    for alias, canonical in UNIT_ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', t):
            unit = canonical
            break
    if unit is None:
        unit = DEFAULT_UNIT.get(item_en, "kg")

    item_nepali = ITEM_MAP.get(item_en, item_en)

    return {"intent": action, "item": item_nepali, "qty": float(qty), "unit": unit}


# ══════════════════════════════════════════════════════════════════════════════
# LLM SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class LLMService:
    def __init__(self):
        self.api_url     = "http://localhost:11434/api/generate"
        self.model       = "llama3"
        self.valid_items = list(ITEM_MAP.values())

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

    def _validate_json(self, data: dict) -> dict:
        intent = str(data.get("intent", "")).upper()
        if intent not in ("ADD", "REMOVE", "CHECK"):
            intent = "ADD"

        item_raw = str(data.get("item", "")).strip()
        if item_raw in self.valid_items:
            item = item_raw
        else:
            item_en  = item_raw.replace(" ", "_").title()
            item     = ITEM_MAP.get(item_en)
            if item is None:
                item_lower = item_raw.lower()
                item = next(
                    (v for v in self.valid_items if v.lower() == item_lower),
                    "Digestive Biskut"
                )

        try:
            qty = float(data.get("qty", 0))
            if qty < 0:
                qty = 0.0
        except (ValueError, TypeError):
            qty = 0.0

        if intent == "CHECK":
            qty = 0.0

        unit = str(data.get("unit", "")).lower().strip()
        if unit not in ("kg", "pieces", "packet", "liter"):
            item_en_lookup = NEPALI_TO_EN.get(item, "Rice")
            unit = DEFAULT_UNIT.get(item_en_lookup, "kg")

        return {"intent": intent, "item": item, "qty": qty, "unit": unit}

    def process_text(self, text: str) -> dict | None:
        print(f"\n🧠 [Agent 1] Analyzing: '{text}'")

        regex_result = _regex_parse(text)
        if regex_result:
            print(f"⚡ Regex parser: {regex_result}")
            return regex_result

        print("🤖 Regex inconclusive — calling Llama3...")
        try:
            a1_prompt    = AGENT1_PROMPT_TEMPLATE.format(text=text)
            cot_response = self._call_ollama(a1_prompt, format_json=False)
            print(f"   ↳ AI Logic:\n{cot_response}")

            clean_english = ""
            for line in cot_response.split("\n"):
                if line.strip().lower().startswith("translation:"):
                    clean_english = line.split(":", 1)[1].strip()
                    break
            if not clean_english:
                lines = [l.strip() for l in cot_response.split("\n") if l.strip()]
                clean_english = lines[-1] if lines else text

            print(f"   ↳ Translated: '{clean_english}'")

            regex_on_clean = _regex_parse(clean_english)
            if regex_on_clean:
                print(f"⚡ Regex on clean: {regex_on_clean}")
                return regex_on_clean

            print("🧠 [Agent 2] Extracting JSON...")
            a2_prompt = AGENT2_PROMPT_TEMPLATE.format(command=clean_english)
            json_str  = self._call_ollama(a2_prompt, format_json=True)
            print(f"   ↳ Raw JSON: {json_str!r}")

            raw_data  = json.loads(json_str)
            validated = self._validate_json(raw_data)
            print(f"   ↳ Validated: {validated}")
            return validated

        except json.JSONDecodeError as e:
            print(f"❌ JSON error: {e}")
            return None
        except requests.RequestException as e:
            print(f"❌ Ollama error: {e}")
            return None
        except Exception as e:
            print(f"❌ LLM error: {e}")
            return None