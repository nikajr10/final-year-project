"""
whisper_service.py
==================
Nepali Voice Inventory System — Audio Transcription + Pre-processing

PERMANENT NUMBER SOLUTION:
  Step 0: Convert Devanagari digit characters (१२३...) → Arabic (123...)
           This handles ANY number of any size, forever.
  Step 1: Exact dict — Nepali number words (एक, दुई, ... सय) → digits
  Step 2: Exact dict — items, units, actions
  Step 3: Prefix-tree — catches any Devanagari item/action mishear not in dict
  Step 4: Deduplicate repeated canonical tokens

DEVANAGARI PREFIX-TREE (item disambiguation by character):
  ┌─────────────────────────────────────────────────────────────────┐
  │  1st CHAR  →  ITEM                                             │
  │  अ  → Eggs                                                     │
  │  ड  → Lentils   (only ड, NOT द — see NUMBER SAFETY note)      │
  │  त  → Oil                                                      │
  │  न  → Salt                                                     │
  │  म  → Flour  (covers महिदा, मेदा, मईदा, मइदा, माइदा, ...)    │
  │  व  → Turmeric  (वेसार alternate)                             │
  │  च + चा → Rice                                                 │
  │  च + चि + चिन → Sugar                                         │
  │  च + चि + चिउ/चिो → Beaten_Rice                              │
  │  ब + बे → Turmeric                                             │
  │  ब + बि → Biscuits                                             │
  │  ब + बढ → Add (verb)                                           │
  │                                                                 │
  │  NUMBER SAFETY: द-words (दाल excluded intentionally)           │
  │  All Nepali number words starting with द (दश, दस, दास, दुई,   │
  │  दुइटा) are caught in STEP 1 dict BEFORE the prefix tree runs. │
  │  The prefix tree only sees द if dict missed it → Lentils.      │
  └─────────────────────────────────────────────────────────────────┘
"""

import re
import whisper


# ══════════════════════════════════════════════════════════════════════════════
# DEVANAGARI DIGIT CHARACTERS → ARABIC DIGITS
# Handles numbers like १०, ५, २५, १००, ५०० — any size, permanently
# ══════════════════════════════════════════════════════════════════════════════

_DEVA_DIGITS = "०१२३४५६७८९"

def _convert_devanagari_numerals(text: str) -> str:
    """
    Convert Devanagari digit characters to Arabic digits.
    '१०' → '10',  '५०' → '50',  '१२३' → '123', etc.
    Works for any number, no upper limit.
    """
    return "".join(
        str(_DEVA_DIGITS.index(ch)) if ch in _DEVA_DIGITS else ch
        for ch in text
    )


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — EXACT MATCH DICTIONARY
# Numbers MUST come before items/actions — number words like दश, दस, दास
# start with 'द' which is also the first char of दाल (Lentils).
# Dict replaces them first so prefix-tree never sees them as Lentils.
# ══════════════════════════════════════════════════════════════════════════════

CORRECTIONS = {

    # ──────────────────────────────────────────────────────────────────────────
    # NUMBERS 1–10 (Devanagari words + Romanized + hallucinations)
    # ──────────────────────────────────────────────────────────────────────────

    "एउटा": "1", "एक": "1", "एउ": "1",
    "ek": "1", "aek": "1", "euta": "1", "euka": "1",

    "दुइटा": "2", "दुई": "2", "दो": "2", "दुइ": "2",
    "dui": "2", "duitaa": "2",

    "तीन": "3", "तिन": "3", "तिनु": "3",
    "teen": "3", "tin": "3", "tiin": "3",

    "चार": "4", "चारु": "4",
    "char": "4", "chaar": "4",

    # पाथ्स is a real Whisper hallucination for पाँच
    "पाँच": "5", "पाच": "5", "पाथ्स": "5",
    "paanch": "5", "panch": "5", "paach": "5", "paanche": "5",

    # छ in Nepali = BOTH "6" AND "is/are" (grammatical).
    # In inventory questions like "कति बाँकी छ" (how much is left?),
    # छ is always the grammatical "is" → map to Check.
    # For the number 6, users say "chha/chah" (Romanized) or type "6" as digit.
    # Standalone Devanagari छ = grammatical marker → Check.
    "छ": "Check",
    "chha": "6", "chah": "6", "chhah": "6",

    "सात": "7", "साात": "7",
    "saat": "7", "saath": "7",

    "आठ": "8",
    "aath": "8", "ath": "8", "aate": "8", "aatha": "8",

    "नौ": "9", "नौं": "9",
    "nau": "9", "naw": "9", "noo": "9", "nou": "9",

    # 10 — IMPORTANT: दश/दस/दास start with 'द' same as दाल.
    # Must be caught HERE before prefix tree runs.
    "दश": "10", "दस": "10", "दास": "10", "दाश": "10",
    "das": "10", "dass": "10", "dasa": "10", "dash": "10",

    # ──────────────────────────────────────────────────────────────────────────
    # NUMBERS 11–19
    # ──────────────────────────────────────────────────────────────────────────

    "एघार": "11", "एघारा": "11", "eghar": "11",
    "बाह्र": "12", "बाह्रा": "12", "bahra": "12",
    "तेह्र": "13", "तेह्रा": "13", "tehra": "13",
    "चौध": "14", "चौधा": "14", "chaudha": "14",
    "पन्ध्र": "15", "पन्ध्रा": "15", "pandhra": "15",
    "सोह्र": "16", "सोह्रा": "16", "sohra": "16",
    "सत्र": "17", "सत्रा": "17", "satra": "17",
    "अठार": "18", "अठारा": "18", "athara": "18",
    "उन्नाइस": "19", "unnaisa": "19",

    # ──────────────────────────────────────────────────────────────────────────
    # NUMBERS 20–100 (tens + most common compounds)
    # ──────────────────────────────────────────────────────────────────────────

    "बीस": "20", "बिस": "20", "bees": "20", "bis": "20",
    "एकाइस": "21", "ekkais": "21",
    "बाइस": "22", "baais": "22",
    "तेइस": "23", "teis": "23",
    "चौबीस": "24", "chaubis": "24",
    "पच्चीस": "25", "पचिस": "25", "pachis": "25",
    "छब्बीस": "26", "chhabbis": "26",
    "सत्ताइस": "27", "sattais": "27",
    "अट्ठाइस": "28", "atthais": "28",
    "उनन्तीस": "29", "unantis": "29",

    "तीस": "30", "तिस": "30", "tis": "30", "tees": "30",
    "एकतीस": "31", "एकतिस": "31",
    "बत्तीस": "32", "बत्तिस": "32",
    "तेत्तीस": "33", "तेत्तिस": "33",
    "चौंतीस": "34", "चौतिस": "34",
    "पैंतीस": "35", "पैतिस": "35", "paintis": "35",
    "छत्तीस": "36", "छत्तिस": "36",
    "सैंतीस": "37", "सैतिस": "37",
    "अठतीस": "38", "अठतिस": "38",
    "उनन्चालीस": "39",

    "चालीस": "40", "चालिस": "40", "chalis": "40",
    "एकचालीस": "41",
    "बयालीस": "42",
    "त्रिचालीस": "43",
    "चवालीस": "44",
    "पैंतालीस": "45", "पैतालिस": "45", "paintalis": "45",
    "छयालीस": "46",
    "सैंतालीस": "47",
    "अठचालीस": "48",
    "उनन्पचास": "49",

    "पचास": "50", "पचाँस": "50", "pachas": "50",
    "एकाउन्न": "51",
    "बाउन्न": "52",
    "त्रिपन्न": "53",
    "चउन्न": "54",
    "पचपन्न": "55", "पचपन": "55", "pachpan": "55",
    "छपन्न": "56",
    "सन्ताउन्न": "57",
    "अन्ठाउन्न": "58",
    "उनसाठी": "59",

    "साठी": "60", "साठि": "60", "साठ्ठी": "60", "sathi": "60",
    "एकसाठी": "61",
    "बैसाठी": "62",
    "त्रिसाठी": "63",
    "चौंसाठी": "64",
    "पैंसठी": "65", "पैसठि": "65", "painsathi": "65",
    "छैसठी": "66",
    "सत्सठी": "67",
    "अठसठी": "68",
    "उनहत्तर": "69",

    "सत्तरी": "70", "सत्तरि": "70", "sattari": "70",
    "एकहत्तर": "71",
    "बहत्तर": "72",
    "त्रिहत्तर": "73",
    "चौहत्तर": "74",
    "पचहत्तर": "75", "pachhattara": "75",
    "छहत्तर": "76",
    "सत्हत्तर": "77",
    "अठहत्तर": "78",
    "उनासी": "79",

    "असी": "80", "असि": "80", "asi": "80",
    "एकासी": "81",
    "बयासी": "82",
    "त्रियासी": "83",
    "चौरासी": "84",
    "पचासी": "85", "पचासि": "85",
    "छयासी": "86",
    "सत्यासी": "87",
    "अठासी": "88",
    "उनान्नब्बे": "89",

    "नब्बे": "90", "nabbe": "90",
    "एकानब्बे": "91",
    "बयानब्बे": "92",
    "त्रियानब्बे": "93",
    "चौरानब्बे": "94",
    "पचानब्बे": "95", "pachanabbe": "95",
    "छयानब्बे": "96",
    "सत्यानब्बे": "97",
    "अन्ठानब्बे": "98",
    "उनान्सय": "99",

    "सय": "100", "एकसय": "100", "say": "100",

    # ──────────────────────────────────────────────────────────────────────────
    # UNITS
    # ──────────────────────────────────────────────────────────────────────────

    "किलोग्राम": "kg", "किलोग": "kg", "किलो": "kg", "किलु": "kg",
    "kilo": "kg", "killo": "kg", "kilu": "kg", "kilogram": "kg",

    "सोटा": "pieces", "ओटा": "pieces", "ओता": "pieces",
    "वटा": "pieces", "वाटा": "pieces", "भटा": "pieces",
    "गोटा": "pieces", "गोटो": "pieces",
    "wata": "pieces", "ota": "pieces", "vata": "pieces",
    "gota": "pieces", "bata": "pieces", "otta": "pieces",
    "piece": "pieces", "pieces": "pieces",

    "प्याकेट": "packet", "प्याकेटहरू": "packet",
    "पोका": "packet", "पोको": "packet", "पकेट": "packet",
    "packet": "packet", "packets": "packet",
    "pakit": "packet", "pyaket": "packet", "poka": "packet",

    "लिटर": "liter", "लिटरहरू": "liter", "लिटार": "liter",
    "liter": "liter", "litre": "liter", "litar": "liter",
    "liters": "liter", "litres": "liter",

    # ──────────────────────────────────────────────────────────────────────────
    # ITEMS — DEVANAGARI
    # ──────────────────────────────────────────────────────────────────────────

    # Rice — चामल
    "चामल": "Rice", "चाामल": "Rice", "चाम": "Rice",
    "चामल्": "Rice", "चामाल": "Rice", "चामले": "Rice",

    # Lentils — दाल / डाल
    "दाल": "Lentils", "डाल": "Lentils",
    "दाल्": "Lentils", "दालहरू": "Lentils", "दाले": "Lentils",

    # Salt — नुन
    "नुन": "Salt", "नून": "Salt", "नुन्": "Salt",
    "नुने": "Salt", "नुनु": "Salt",

    # Sugar — चिनी / चिनि
    "चिनी": "Sugar", "चिनि": "Sugar", "चिनिः": "Sugar",
    "चिनिहरू": "Sugar", "चिन्": "Sugar", "चिनो": "Sugar",

    # Oil — तेल
    "तेल": "Oil", "तेल्": "Oil", "तेलहरू": "Oil",
    "तैल": "Oil", "तेलो": "Oil",

    # Flour — मैदा + ALL म-mishears (म is unique first char)
    "मैदा": "Flour", "महिदा": "Flour", "मेदा": "Flour",
    "मइदा": "Flour", "माइदा": "Flour", "मईदा": "Flour",
    "मेइदा": "Flour", "मेहिदा": "Flour", "माइदाा": "Flour",
    "मैदो": "Flour", "मैदाा": "Flour", "मैिदा": "Flour", "मिदा": "Flour",

    # Turmeric — बेसार / वेसार
    "बेसार": "Turmeric", "बेसाड": "Turmeric", "बेसार्": "Turmeric",
    "बेसारहरू": "Turmeric", "बेसाारा": "Turmeric", "बेसारो": "Turmeric",
    "वेसार": "Turmeric", "वेसाड": "Turmeric", "वेसारु": "Turmeric",

    # Eggs — अण्डा / अन्डा / अंडा (common alternate with anusvara)
    "अण्डा": "Eggs", "अन्डा": "Eggs", "अड़ा": "Eggs",
    "अन्डो": "Eggs", "अन्डाहरू": "Eggs", "अण्डो": "Eggs",
    "अाण्डा": "Eggs", "अन्डे": "Eggs",
    "अंडा": "Eggs",   # ← anusvara form Whisper commonly outputs

    # Beaten_Rice — चिउरा
    "चिउरा": "Beaten_Rice", "चिउरो": "Beaten_Rice",
    "चिउराहरू": "Beaten_Rice", "चिउर": "Beaten_Rice",

    # Biscuits — बिस्कुट / बिस्किट
    "बिस्कुट": "Biscuits", "बिस्किट": "Biscuits",
    "बिस्कुट्": "Biscuits", "बिस्कुटहरू": "Biscuits",
    "बिस्किटहरू": "Biscuits", "बिस्कोट": "Biscuits",

    # ──────────────────────────────────────────────────────────────────────────
    # ITEMS — ROMANIZED
    # ──────────────────────────────────────────────────────────────────────────

    "chamal": "Rice", "chaamal": "Rice", "chaaml": "Rice",
    "ryce": "Rice", "samal": "Rice", "rice": "Rice",

    "daal": "Lentils", "dal": "Lentils", "dhal": "Lentils",
    "daall": "Lentils", "lentils": "Lentils", "lentil": "Lentils",

    "nun": "Salt", "noon": "Salt", "nune": "Salt",
    "nunu": "Salt", "nuun": "Salt", "salt": "Salt",

    "cheeni": "Sugar", "chini": "Sugar", "sini": "Sugar",
    "chene": "Sugar", "cheene": "Sugar", "chine": "Sugar", "sugar": "Sugar",

    "tel": "Oil", "tail": "Oil", "tayl": "Oil",
    "teel": "Oil", "tell": "Oil", "oil": "Oil",

    "maida": "Flour", "mahida": "Flour", "maeda": "Flour",
    "maita": "Flour", "meda": "Flour", "mayda": "Flour",
    "meida": "Flour", "maheda": "Flour", "flour": "Flour",

    "besar": "Turmeric", "besaar": "Turmeric", "beasar": "Turmeric",
    "beasaar": "Turmeric", "turmeric": "Turmeric", "haldi": "Turmeric",

    "anda": "Eggs", "unda": "Eggs", "ando": "Eggs",
    "aanda": "Eggs", "eggs": "Eggs", "egg": "Eggs",

    "chiura": "Beaten_Rice", "chiuraa": "Beaten_Rice",
    "chiora": "Beaten_Rice", "chiuro": "Beaten_Rice",
    "beaten rice": "Beaten_Rice", "beaten_rice": "Beaten_Rice",

    "biskut": "Biscuits", "biscut": "Biscuits",
    "biscuit": "Biscuits", "biscuits": "Biscuits", "biskutt": "Biscuits",

    # ──────────────────────────────────────────────────────────────────────────
    # ACTIONS — DEVANAGARI
    # ──────────────────────────────────────────────────────────────────────────

    # REMOVE — stock DOWN
    "घटाउ": "Remove", "घटाउँ": "Remove", "घटायो": "Remove",
    "घटाइ": "Remove", "घटा": "Remove", "घटाव": "Remove",
    "घटाउछ": "Remove", "घटाउनु": "Remove",
    "गटाउ": "Remove",        # Whisper mishear of घटाउ
    "अटाव": "Remove",        # Whisper hallucination
    "बेच्यो": "Remove", "बेच": "Remove", "बेचिन्छ": "Remove",
    "हटाउ": "Remove", "हटा": "Remove", "हटायो": "Remove",
    "निकाल": "Remove", "निकाल्यो": "Remove",
    "खर्च": "Remove", "खर्च्यो": "Remove",
    "बिक्यो": "Remove", "बिक्री": "Remove",

    # ADD — stock UP
    "बढाउ": "Add", "बढाउँ": "Add", "बढायो": "Add",
    "बढाइ": "Add", "बढा": "Add", "बढ्यो": "Add",
    "बढाउछ": "Add", "बढाउनु": "Add",
    "थप्यो": "Add", "थपा": "Add", "थापा": "Add", "थप": "Add", "धपा": "Add", "थावा": "Add",
    "थबा": "Add", "थाबा": "Add",
    "थपिन्छ": "Add", "थपियो": "Add",
    "किन्यो": "Add", "किन्छु": "Add", "किन्यौं": "Add",
    "राख्यो": "Add", "राख": "Add", "राखियो": "Add",
    "आयो": "Add", "आउँछ": "Add",

    # CHECK — query stock
    "बाँकी": "Check", "बाँकि": "Check", "बाकी": "Check",
    "बागी": "Check",          # real log mishear of बाँकी
    "बाँकिछ": "Check", "बाँकिछन्": "Check",
    "कति": "Check", "कतिवटा": "Check", "कतिओटा": "Check",
    "कोटी": "Check",          # real log mishear of कति
    "कोती": "Check",
    "छाँ": "Check",           # trailing "छ" in "कति बाँकी छ"
    "छन्": "Check",
    "चेक": "Check", "स्टक": "Check",

    # ──────────────────────────────────────────────────────────────────────────
    # ACTIONS — ROMANIZED
    # ──────────────────────────────────────────────────────────────────────────

    "ghatau": "Remove", "ghataau": "Remove", "ghata": "Remove",
    "ghatayo": "Remove", "ghatai": "Remove",
    "bech": "Remove", "bechyo": "Remove",
    "hatau": "Remove", "hatayo": "Remove",
    "nikal": "Remove", "nikalyo": "Remove",
    "kharch": "Remove", "kharchyo": "Remove",
    "bikyo": "Remove", "bikri": "Remove",
    "remove": "Remove", "sell": "Remove", "sold": "Remove",
    "decrease": "Remove", "reduce": "Remove",

    "badhau": "Add", "badhaau": "Add", "badhayo": "Add",
    "badha": "Add", "badhyo": "Add", "badhaaou": "Add",
    "thap": "Add", "thapaau": "Add", "thapyo": "Add", "thaba": "Add", "thaaba": "Add",
    "kinyo": "Add", "kinchhau": "Add",
    "rakh": "Add", "rakhyo": "Add",
    "aayo": "Add", "aaucha": "Add",
    "add": "Add", "increase": "Add", "bought": "Add",

    "banki": "Check", "baaki": "Check", "baki": "Check",
    "baagi": "Check",
    "kati": "Check", "katiwata": "Check",
    "koti": "Check",
    "check": "Check", "stock": "Check",
    "how much": "Check", "how many": "Check",
}

# Quick lookup sets
_ITEMS   = {"Rice","Lentils","Salt","Sugar","Oil","Flour",
             "Turmeric","Eggs","Beaten_Rice","Biscuits"}
_ACTIONS = {"Add","Remove","Check"}
_UNITS   = {"kg","pieces","packet","liter"}


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — DEVANAGARI PREFIX-TREE
# Safety net for any Devanagari word the dict missed.
# Number words are already replaced in Layer 1, so 'द' here means Lentils.
# ══════════════════════════════════════════════════════════════════════════════

def _devanagari_prefix_match(word: str) -> str | None:
    w = word.strip("।.,!? \t\n")
    if not w:
        return None

    c1 = w[0]
    c2 = w[1] if len(w) > 1 else ""
    c3 = w[2] if len(w) > 2 else ""

    # Unique first characters
    if c1 == "अ":           return "Eggs"
    if c1 == "ड":           return "Lentils"   # only ड here — not द (numbers caught in dict)
    if c1 == "द":           return "Lentils"   # दाल; दश/दस/दास already replaced in dict
    if c1 == "त":           return "Oil"
    if c1 == "न":           return "Salt"
    if c1 == "म":           return "Flour"     # ALL मX → Flour (unique)
    if c1 == "व":           return "Turmeric"  # वेसार alternate

    # च — needs 2nd char
    if c1 == "च":
        if c2 == "ा":       return "Rice"          # चा → चामल
        if c2 == "ि":
            if c3 == "न":   return "Sugar"          # चिन → चिनी
            return "Beaten_Rice"                    # चिउ/चिो → चिउरा
        return "Rice"                               # fallback चX

    # ब — needs 2nd char
    if c1 == "ब":
        if c2 == "े":       return "Turmeric"       # बे → बेसार
        if c2 == "ि":       return "Biscuits"       # बि → बिस्कुट
        if c2 == "ढ":       return "Add"            # बढ → बढाउ verb
        if c2 == "ा":       return "Check"          # बाँकी (should be in dict but safety)

    return None


def _is_devanagari(s: str) -> bool:
    return any("\u0900" <= ch <= "\u097F" for ch in s)


# ══════════════════════════════════════════════════════════════════════════════
# WHISPER SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class WhisperService:
    def __init__(self):
        print("🔄 Loading Whisper model (medium)...")
        self.model = whisper.load_model("medium")
        print("✅ Whisper Loaded Successfully")

    def _clean(self, text: str) -> str:
        """
        Full cleaning pipeline:
          Step 0: Devanagari numeral chars → Arabic  (१० → 10, infinite numbers)
          Step 1: Normalise punctuation
          Step 2: Layer 1 dict (longest key first)
          Step 3: Layer 2 prefix-tree for remaining Devanagari
          Step 4: Rebuild with canonical casing
          Step 5: Deduplicate repeated action tokens
        """

        # ── Step 0: Devanagari digits → Arabic digits ─────────────────────────
        # Must run BEFORE any other step so १० → 10 before dict sees it
        text = _convert_devanagari_numerals(text)

        # ── Step 1: Normalise punctuation ─────────────────────────────────────
        for ch in "।.,!?":
            text = text.replace(ch, " ")

        # ── Step 2: Layer 1 exact dict ────────────────────────────────────────
        # Longest key first prevents partial matches (e.g. "paanch" before "pan")
        lowered = text.lower()

        for key in sorted(CORRECTIONS.keys(), key=len, reverse=True):
            val     = CORRECTIONS[key]
            lowered = lowered.replace(key.lower(), f" {val.lower()} ")
            text    = text.replace(key, f" {val} ")

        # ── Step 3: Layer 2 prefix-tree for leftover Devanagari ───────────────
        tokens   = text.split()
        resolved = []
        for tok in tokens:
            t = tok.strip()
            if _is_devanagari(t):
                match = _devanagari_prefix_match(t)
                if match:
                    print(f"   🌳 Prefix-tree: '{t}' → '{match}'")
                    resolved.append(match.lower())
                else:
                    print(f"   ❓ Dropping unrecognised Devanagari: '{t}'")
                    # Intentionally not appended — it's noise
            else:
                resolved.append(t.lower())

        # Merge prefix-tree output back into lowered
        lowered = " ".join(resolved)

        # ── Step 4: Rebuild with proper capitalisation ─────────────────────────
        final = []
        for w in lowered.split():
            w = w.strip()
            if not w:
                continue
            if w == "beaten_rice":
                final.append("Beaten_Rice")
            elif w in {i.lower() for i in _ITEMS}:
                final.append(w.capitalize())
            elif w in {a.lower() for a in _ACTIONS}:
                final.append(w.capitalize())
            elif w in _UNITS or w.isdigit():
                final.append(w)
            else:
                final.append(w)

        # ── Step 5: Deduplicate — keep first occurrence of every token ───────────
        # Whisper often outputs both Nepali + Romanized for the same word,
        # producing e.g. "10 kg Sugar Add 10 kg Sugar Add".
        # For short inventory commands, every meaningful token should appear once.
        seen     = set()
        deduped  = []
        for w in final:
            if w not in seen:
                seen.add(w)
                deduped.append(w)

        result = " ".join(w for w in deduped if w)
        result = " ".join(result.split())
        return result

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe Nepali audio → cleaned English-token string.
        """
        initial_prompt = (
            "chamal daal nun chini tel maida besar anda chiura biskut "
            "चामल दाल नुन चिनी तेल मैदा बेसार अण्डा चिउरा बिस्कुट "
            "thap badhau ghatau check add remove "
            "थप बढाउ घटाउ बाँकी कति "
            "ek dui tin char paanch 1 2 3 4 5 6 7 8 9 10 "
            "kilo wata packet liter kg pieces "
            "किलो वटा प्याकेट लिटर"
        )

        result = self.model.transcribe(
            audio_path,
            language="ne",
            initial_prompt=initial_prompt,
            task="transcribe",
            beam_size=8,
            temperature=0.0,
            fp16=False,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
        )

        raw_text = result["text"].strip()
        if len(raw_text) < 2:
            return ""

        cleaned = self._clean(raw_text)
        print(f"🎙️  RAW     : {raw_text!r}")
        print(f"✅  CLEANED : {cleaned!r}")

        return cleaned