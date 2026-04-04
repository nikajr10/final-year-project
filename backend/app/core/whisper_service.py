"""
whisper_service.py
==================
Nepali Voice Inventory System — Audio Transcription + Pre-processing

BISCUIT ROUTING LOGIC:
  "tiger biscuit"    → Tiger Biscuit     (multi-word dict entry, caught first)
  "digestive biscuit"→ Digestive Biscuit (multi-word dict entry, caught first)
  "biscuit" alone    → Digestive Biscuit (synonym fallback rule)
"""

import re
import whisper

_DEVA_DIGITS = "०१२३४५६७८९"


def _convert_devanagari_numerals(text: str) -> str:
    return "".join(
        str(_DEVA_DIGITS.index(ch)) if ch in _DEVA_DIGITS else ch
        for ch in text
    )


CORRECTIONS = {

    # ══════════════════════════════════════════════════════════════════════════
    # MULTI-WORD ITEMS — must be here so longest-key-first catches them
    # BEFORE the single-word "biscuit" entry fires.
    # ══════════════════════════════════════════════════════════════════════════

    # Tiger Biscuit — all phonetic variants
    "tiger biscuit":     "Tiger Biscuit",
    "tiger biscuits":    "Tiger Biscuit",
    "tiger biskut":      "Tiger Biscuit",
    "tiger biskutt":     "Tiger Biscuit",
    "tiger biscut":      "Tiger Biscuit",
    "taiger biscuit":    "Tiger Biscuit",
    "taiger biskut":     "Tiger Biscuit",
    "tigger biscuit":    "Tiger Biscuit",
    "tigger biskut":     "Tiger Biscuit",
    "टाइगर बिस्कुट":    "Tiger Biscuit",
    "टाइगर बिस्किट":    "Tiger Biscuit",

    # Digestive Biscuit — all phonetic variants
    "digestive biscuit":  "Digestive Biscuit",
    "digestive biscuits": "Digestive Biscuit",
    "digestive biskut":   "Digestive Biscuit",
    "digestive biskutt":  "Digestive Biscuit",
    "digestive biscut":   "Digestive Biscuit",
    "dajestiv biscuit":   "Digestive Biscuit",
    "daigestive biscuit": "Digestive Biscuit",
    "dijestive biscuit":  "Digestive Biscuit",
    "डाइजेस्टिभ बिस्कुट": "Digestive Biscuit",
    "डाइजेस्टिभ बिस्किट": "Digestive Biscuit",

    # ══════════════════════════════════════════════════════════════════════════
    # NUMBERS 1–10
    # ══════════════════════════════════════════════════════════════════════════

    "एउटा": "1", "एक": "1", "एउ": "1",
    "ek": "1", "aek": "1", "euta": "1", "euka": "1",

    "दुइटा": "2", "दुई": "2", "दो": "2", "दुइ": "2",
    "dui": "2", "duitaa": "2",

    "तीन": "3", "तिन": "3", "तिनु": "3",
    "teen": "3", "tin": "3", "tiin": "3",

    "चार": "4", "चारु": "4",
    "char": "4", "chaar": "4",

    "पाँच": "5", "पाच": "5", "पाथ्स": "5",
    "paanch": "5", "panch": "5", "paach": "5", "paanche": "5",

    "छ": "Check",
    "chha": "6", "chah": "6", "chhah": "6",

    "सात": "7", "साात": "7",
    "saat": "7", "saath": "7",

    "आठ": "8",
    "aath": "8", "ath": "8", "aate": "8", "aatha": "8",

    "नौ": "9", "नौं": "9",
    "nau": "9", "naw": "9", "noo": "9", "nou": "9",

    "दश": "10", "दस": "10", "दास": "10", "दाश": "10",
    "das": "10", "dass": "10", "dasa": "10", "dash": "10",

    # ══════════════════════════════════════════════════════════════════════════
    # NUMBERS 11–100
    # ══════════════════════════════════════════════════════════════════════════

    "एघार": "11", "एघारा": "11", "eghar": "11",
    "बाह्र": "12", "बाह्रा": "12", "bahra": "12",
    "तेह्र": "13", "तेह्रा": "13", "tehra": "13",
    "चौध": "14", "चौधा": "14", "chaudha": "14",
    "पन्ध्र": "15", "पन्ध्रा": "15", "pandhra": "15",
    "सोह्र": "16", "सोह्रा": "16", "sohra": "16",
    "सत्र": "17", "सत्रा": "17", "satra": "17",
    "अठार": "18", "अठारा": "18", "athara": "18",
    "उन्नाइस": "19", "unnaisa": "19",

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

    # ══════════════════════════════════════════════════════════════════════════
    # UNITS
    # ══════════════════════════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════════════════════════
    # ITEMS — DEVANAGARI (single-word)
    # ══════════════════════════════════════════════════════════════════════════

    "चामल": "Rice", "चाामल": "Rice", "चाम": "Rice",
    "चामल्": "Rice", "चामाल": "Rice", "चामले": "Rice",

    "दाल": "Lentils", "डाल": "Lentils",
    "दाल्": "Lentils", "दालहरू": "Lentils", "दाले": "Lentils",

    "नुन": "Salt", "नून": "Salt", "नुन्": "Salt",
    "नुने": "Salt", "नुनु": "Salt",

    "चिनी": "Sugar", "चिनि": "Sugar", "चिनिः": "Sugar",
    "चिनिहरू": "Sugar", "चिन्": "Sugar", "चिनो": "Sugar",

    "तेल": "Oil", "तेल्": "Oil", "तेलहरू": "Oil",
    "तैल": "Oil", "तेलो": "Oil",

    "मैदा": "Flour", "महिदा": "Flour", "मेदा": "Flour",
    "मइदा": "Flour", "माइदा": "Flour", "मईदा": "Flour",
    "मेइदा": "Flour", "मेहिदा": "Flour", "माइदाा": "Flour",
    "मैदो": "Flour", "मैदाा": "Flour", "मैिदा": "Flour", "मिदा": "Flour",

    "बेसार": "Turmeric", "बेसाड": "Turmeric", "बेसार्": "Turmeric",
    "बेसारहरू": "Turmeric", "बेसाारा": "Turmeric", "बेसारो": "Turmeric",
    "वेसार": "Turmeric", "वेसाड": "Turmeric", "वेसारु": "Turmeric",

    "अण्डा": "Eggs", "अन्डा": "Eggs", "अड़ा": "Eggs",
    "अन्डो": "Eggs", "अन्डाहरू": "Eggs", "अण्डो": "Eggs",
    "अाण्डा": "Eggs", "अन्डे": "Eggs",
    "अंडा": "Eggs",

    "चिउरा": "Beaten_Rice", "चिउरो": "Beaten_Rice",
    "चिउराहरू": "Beaten_Rice", "चिउर": "Beaten_Rice",

    # Generic biscuit (single word) → stays as "Biscuits" here;
    # synonym rule in Step 6 upgrades it to "Digestive Biscuit"
    "बिस्कुट": "Biscuits", "बिस्किट": "Biscuits",
    "बिस्कुट्": "Biscuits", "बिस्कुटहरू": "Biscuits",
    "बिस्किटहरू": "Biscuits", "बिस्कोट": "Biscuits",

    # ══════════════════════════════════════════════════════════════════════════
    # ITEMS — ROMANIZED (single-word)
    # ══════════════════════════════════════════════════════════════════════════

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

    # Generic biscuit single-word forms — synonym rule upgrades to Digestive Biscuit
    "biskut": "Biscuits", "biscut": "Biscuits",
    "biscuit": "Biscuits", "biscuits": "Biscuits", "biskutt": "Biscuits",

    # ══════════════════════════════════════════════════════════════════════════
    # ACTIONS — DEVANAGARI
    # ══════════════════════════════════════════════════════════════════════════

    "घटाउ": "Remove", "घटाउँ": "Remove", "घटायो": "Remove",
    "घटाइ": "Remove", "घटा": "Remove", "घटाव": "Remove",
    "घटाउछ": "Remove", "घटाउनु": "Remove",
    "गटाउ": "Remove",
    "अटाव": "Remove",
    "बेच्यो": "Remove", "बेच": "Remove", "बेचिन्छ": "Remove",
    "हटाउ": "Remove", "हटा": "Remove", "हटायो": "Remove",
    "निकाल": "Remove", "निकाल्यो": "Remove",
    "खर्च": "Remove", "खर्च्यो": "Remove",
    "बिक्यो": "Remove", "बिक्री": "Remove",

    "बढाउ": "Add", "बढाउँ": "Add", "बढायो": "Add",
    "बढाइ": "Add", "बढा": "Add", "बढ्यो": "Add",
    "बढाउछ": "Add", "बढाउनु": "Add",
    "थप्यो": "Add", "थपा": "Add", "थापा": "Add", "थप": "Add", "धपा": "Add", "थावा": "Add",
    "थपिन्छ": "Add", "थपियो": "Add",
    "किन्यो": "Add", "किन्छु": "Add", "किन्यौं": "Add",
    "राख्यो": "Add", "राख": "Add", "राखियो": "Add",
    "आयो": "Add", "आउँछ": "Add",

    "बाँकी": "Check", "बाँकि": "Check", "बाकी": "Check",
    "बागी": "Check",
    "बाँकिछ": "Check", "बाँकिछन्": "Check",
    "कति": "Check", "कतिवटा": "Check", "कतिओटा": "Check",
    "कोटी": "Check",
    "कोती": "Check",
    "छाँ": "Check",
    "छन्": "Check",
    "चेक": "Check", "स्टक": "Check",

    # ══════════════════════════════════════════════════════════════════════════
    # ACTIONS — ROMANIZED
    # ══════════════════════════════════════════════════════════════════════════

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
    "thap": "Add", "thapaau": "Add", "thapyo": "Add",
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

_ITEMS = {
    "Rice", "Lentils", "Salt", "Sugar", "Oil", "Flour",
    "Turmeric", "Eggs", "Beaten_Rice", "Biscuits",
    "Digestive Biscuit", "Tiger Biscuit",
}
_ACTIONS = {"Add", "Remove", "Check"}
_UNITS   = {"kg", "pieces", "packet", "liter"}

# ══════════════════════════════════════════════════════════════════════════════
# SYNONYM RULES
#
# This runs AFTER the dict replaces multi-word entries.
# By the time we reach here:
#   "tiger biscuit"     → already "Tiger Biscuit"    (dict caught it)
#   "digestive biscuit" → already "Digestive Biscuit" (dict caught it)
#   "biscuit" alone     → still "Biscuits"            (synonym upgrades it)
# ══════════════════════════════════════════════════════════════════════════════

_SYNONYM_RULES: list[dict] = [
    {
        # Only fires on standalone "Biscuits" with NO tiger/digestive context
        "trigger_pattern": re.compile(
            r"\b(biscuits?|biskutt?|biscut)\b",
            re.IGNORECASE,
        ),
        "guard_pattern": re.compile(
            r"\b(tiger|taiger|tigger|taigar"
            r"|digestive|dajestiv|daigestive|dijestive"
            r"|Tiger Biscuit|Digestive Biscuit)\b",
            re.IGNORECASE,
        ),
        "replace_with": "Digestive Biscuit",
        "log_label":    "generic biscuit → Digestive Biscuit",
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# DEVANAGARI PREFIX-TREE
# ══════════════════════════════════════════════════════════════════════════════

def _devanagari_prefix_match(word: str) -> str | None:
    w = word.strip("।.,!? \t\n")
    if not w:
        return None
    c1 = w[0]
    c2 = w[1] if len(w) > 1 else ""
    c3 = w[2] if len(w) > 2 else ""

    if c1 == "अ":  return "Eggs"
    if c1 == "ड":  return "Lentils"
    if c1 == "द":  return "Lentils"
    if c1 == "त":  return "Oil"
    if c1 == "न":  return "Salt"
    if c1 == "म":  return "Flour"
    if c1 == "व":  return "Turmeric"
    if c1 == "च":
        if c2 == "ा":     return "Rice"
        if c2 == "ि":
            if c3 == "न": return "Sugar"
            return "Beaten_Rice"
        return "Rice"
    if c1 == "ब":
        if c2 == "े":  return "Turmeric"
        if c2 == "ि":  return "Biscuits"
        if c2 == "ढ":  return "Add"
        if c2 == "ा":  return "Check"
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

    def _clean(self, text: str) -> tuple[str, int]:
        """
        Returns (cleaned_text, quantity).

        Biscuit routing guaranteed:
          "tiger biscuit"     → Tiger Biscuit     (Step 2 dict, multi-word)
          "digestive biscuit" → Digestive Biscuit (Step 2 dict, multi-word)
          "biscuit" alone     → Digestive Biscuit (Step 6 synonym rule)
        """

        # Step 0: Devanagari digits → Arabic
        text = _convert_devanagari_numerals(text)

        # Step 1: Normalise punctuation
        for ch in "।.,!?":
            text = text.replace(ch, " ")

        # Step 2: Layer-1 exact dict — LONGEST KEY FIRST
        # Multi-word entries like "tiger biscuit" (13 chars) are processed
        # before single-word "biscuit" (7 chars) — no special handling needed.
        lowered = text.lower()
        for key in sorted(CORRECTIONS.keys(), key=len, reverse=True):
            val     = CORRECTIONS[key]
            lowered = lowered.replace(key.lower(), f" {val.lower()} ")
            text    = text.replace(key, f" {val} ")

        # Step 3: Devanagari prefix-tree for leftover Devanagari tokens
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
            else:
                resolved.append(t.lower())

        lowered = " ".join(resolved)

        # Step 4: Rebuild with canonical capitalisation
        final = []
        for w in lowered.split():
            w = w.strip()
            if not w:
                continue
            # Drop single stray characters that aren't digits
            if len(w) == 1 and not w.isdigit():
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

        # Step 5: Deduplicate consecutive identical action tokens
        deduped = []
        prev    = None
        for w in final:
            if w in _ACTIONS and w == prev:
                continue
            deduped.append(w)
            prev = w

        result = " ".join(w for w in deduped if w)
        result = " ".join(result.split())

        # Step 6: Synonym disambiguation
        # At this point:
        #   "Tiger Biscuit" / "Digestive Biscuit" already correct (Step 2)
        #   "Biscuits" (generic) → upgraded to "Digestive Biscuit" here
        for rule in _SYNONYM_RULES:
            trigger_pat: re.Pattern = rule["trigger_pattern"]
            guard_pat:   re.Pattern = rule["guard_pattern"]
            replace:     str        = rule["replace_with"]
            label:       str        = rule["log_label"]

            if guard_pat.search(result):
                print(f"   🛡️  Synonym guard fired — skipping: {label}")
                continue

            if trigger_pat.search(result):
                result = trigger_pat.sub(replace, result)
                result = " ".join(result.split())
                print(f"   🍪 Synonym applied: {label}")

        # Step 7: Extract quantity
        qty_match     = re.search(r"\b(\d+)\b", result)
        extracted_qty = int(qty_match.group(1)) if qty_match else 0

        return result, extracted_qty

    def transcribe(self, audio_path: str) -> tuple[str, int]:
        initial_prompt = (
            "chamal daal nun chini tel maida besar anda chiura biskut "
            "digestive biscuit tiger biscuit "
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
            return "", 0

        cleaned, qty = self._clean(raw_text)
        print(f"🎙️  RAW     : {raw_text!r}")
        print(f"✅  CLEANED : {cleaned!r}  |  QTY: {qty}")
        return cleaned, qty