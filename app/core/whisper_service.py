import re
import whisper


class WhisperService:
    def __init__(self):
        print("🔄 Loading Whisper model (medium)...")
        self.model = whisper.load_model("medium")
        print("✅ Whisper Loaded Successfully")

    def _apply_brute_force_corrections(self, text: str) -> str:
        """
        THE IRON DICTIONARY
        =====================
        Every known Devanagari script word, every Romanized phonetic spelling,
        and every hallucination variant is mapped to one clean canonical English token.

        CANONICAL TOKENS (what the LLM will always receive):
          Numbers  : 1 2 3 4 5 6 7 8 9 10
          Units    : kg  pieces  packet  liter
          Items    : Rice  Lentils  Salt  Sugar  Oil  Flour
                     Turmeric  Eggs  Beaten_Rice  Biscuits
          Actions  : Add  Remove  Check
        """

        corrections = {

            # ══════════════════════════════════════════════
            # NUMBERS
            # ══════════════════════════════════════════════

            # 1 — ek / aek / एक / एउटा
            "एउटा": "1", "एक": "1",
            "ek": "1", "aek": "1", "euta": "1",

            # 2 — dui / do / दुई / दो / दुइटा
            "दुइटा": "2", "दुई": "2", "दो": "2",
            "dui": "2", "do": "2", "duitaa": "2",

            # 3 — teen / tin / तीन / तिन
            "तीन": "3", "तिन": "3",
            "teen": "3", "tin": "3",

            # 4 — char / chaar / चार
            "चार": "4",
            "char": "4", "chaar": "4",

            # 5 — paanch / panch / पाँच / पाच / पाथ्स (hallucination)
            "पाँच": "5", "पाच": "5", "पाथ्स": "5", "पाँच": "5",
            "paanch": "5", "panch": "5", "paach": "5",

            # 6 — cha / chha / छ
            "छ": "6",
            "cha": "6", "chha": "6", "chah": "6",

            # 7 — saat / sat / सात
            "सात": "7",
            "saat": "7", "sat": "7",

            # 8 — aath / ath / आठ
            "आठ": "8",
            "aath": "8", "ath": "8", "aate": "8",

            # 9 — nau / naw / नौ   (never map standalone "no" — too ambiguous)
            "नौ": "9",
            "nau": "9", "naw": "9", "noo": "9",

            # 10 — das / dass / दस / दश / दास (hallucination)
            "दास": "10", "दश": "10", "दस": "10",
            "das": "10", "dass": "10", "dasa": "10",

            # ══════════════════════════════════════════════
            # UNITS
            # ══════════════════════════════════════════════

            # kg / kilo — किलो / किलोग (hallucination)
            "किलोग": "kg", "किलो": "kg",
            "kilo": "kg", "killo": "kg", "kilu": "kg",

            # pieces / wata / ota — वटा / ओटा / ओता / सोटा (hallucination)
            "सोटा": "pieces", "ओटा": "pieces", "ओता": "pieces", "वटा": "pieces",
            "wata": "pieces", "ota": "pieces", "vata": "pieces", "bata": "pieces",
            "gota": "pieces", "otta": "pieces",

            # packet — प्याकेट / पोका
            "प्याकेट": "packet", "पोका": "packet",
            "packet": "packet", "pakit": "packet", "pyaket": "packet",

            # liter — लिटर
            "लिटर": "liter",
            "liter": "liter", "litre": "liter", "litar": "liter",

            # ══════════════════════════════════════════════
            # ITEMS  (10 canonical items)
            # ══════════════════════════════════════════════

            # Rice — चामल / ryce / samal / chamal (hallucinations)
            "चामल": "Rice", "चाम": "Rice",
            "chamal": "Rice", "chaamal": "Rice", "ryce": "Rice",
            "samal": "Rice", "chamaL": "Rice",
            "rice": "Rice",

            # Lentils — दाल / डाल / daal / dal
            "दाल": "Lentils", "डाल": "Lentils",
            "daal": "Lentils", "dal": "Lentils", "dhal": "Lentils",
            "lentils": "Lentils",

            # Salt — नुन / noon / nun
            "नुन": "Salt",
            "nun": "Salt", "noon": "Salt", "nune": "Salt",
            "salt": "Salt",

            # Sugar — चिनी / चिनि / sini / chini
            "चिनी": "Sugar", "चिनि": "Sugar",
            "chini": "Sugar", "sini": "Sugar", "cheeni": "Sugar", "chene": "Sugar",
            "sugar": "Sugar",

            # Oil — तेल / tail / tel
            "तेल": "Oil",
            "tel": "Oil", "tail": "Oil", "tayl": "Oil",
            "oil": "Oil",

            # Flour — मैदा / maida
            "मैदा": "Flour",
            "maida": "Flour", "maeda": "Flour", "maita": "Flour",
            "flour": "Flour",

            # Turmeric — बेसार / वेसार / besar / besaar
            "बेसार": "Turmeric", "वेसार": "Turmeric", "बेसाड": "Turmeric",
            "besar": "Turmeric", "besaar": "Turmeric", "beasar": "Turmeric",
            "turmeric": "Turmeric",

            # Eggs — अण्डा / अन्डा / अड़ा / anda
            "अण्डा": "Eggs", "अन्डा": "Eggs", "अड़ा": "Eggs", "अन्डो": "Eggs",
            "anda": "Eggs", "unda": "Eggs", "ando": "Eggs",
            "eggs": "Eggs", "egg": "Eggs",

            # Beaten_Rice — चिउरा / chiura
            "चिउरा": "Beaten_Rice",
            "chiura": "Beaten_Rice", "chiuraa": "Beaten_Rice", "chiora": "Beaten_Rice",
            "beaten rice": "Beaten_Rice",

            # Biscuits — बिस्कुट / biskut
            "बिस्कुट": "Biscuits", "बिस्किट": "Biscuits",
            "biskut": "Biscuits", "biscut": "Biscuits", "biscuit": "Biscuits",
            "biscuits": "Biscuits",

            # ══════════════════════════════════════════════
            # ACTIONS / VERBS
            # ══════════════════════════════════════════════

            # ── REMOVE (ghatau / ghataau) — stock goes DOWN ──────────────────
            # Devanagari
            "घटाउ": "Remove", "घटाउँ": "Remove", "घटायो": "Remove",
            "घटाइ": "Remove", "घटा": "Remove", "घटाव": "Remove",
            "गटाउ": "Remove",   # common Whisper mishear
            "अटाव": "Remove",   # hallucination
            "बेच्यो": "Remove", "बेच": "Remove", "बेचिन्छ": "Remove",
            "हटाउ": "Remove", "हटा": "Remove", "हटायो": "Remove",
            "निकाल": "Remove", "निकाल्यो": "Remove",
            "खर्च": "Remove", "खर्च्यो": "Remove",
            "बिक्यो": "Remove", "बिक्री": "Remove",
            # Romanized
            "ghatau": "Remove", "ghataau": "Remove", "ghata": "Remove",
            "ghatayo": "Remove", "ghatai": "Remove",
            "bech": "Remove", "bechyo": "Remove",
            "hatau": "Remove", "hatayo": "Remove",
            "nikal": "Remove", "nikalyo": "Remove",
            "kharch": "Remove", "kharchyo": "Remove",
            "bikyo": "Remove", "bikri": "Remove",
            "remove": "Remove", "sell": "Remove", "sold": "Remove",
            "decrease": "Remove", "reduce": "Remove",

            # ── ADD (badhau / thap) — stock goes UP ─────────────────────────
            # Devanagari
            "बढाउ": "Add", "बढाउँ": "Add", "बढायो": "Add",
            "बढाइ": "Add", "बढा": "Add", "बढ्यो": "Add",
            "थप्यो": "Add", "थपा": "Add", "थप": "Add", "धपा": "Add",
            "किन्यो": "Add", "किन्छु": "Add", "किन्यौं": "Add",
            "राख्यो": "Add", "राख": "Add", "राखियो": "Add",
            "आयो": "Add", "आउँछ": "Add",
            "थपिन्छ": "Add", "थपियो": "Add",
            # Romanized
            "badhau": "Add", "badhaau": "Add", "badhayo": "Add",
            "badha": "Add", "badhyo": "Add",
            "thap": "Add", "thapaau": "Add", "thapyo": "Add",
            "kinyo": "Add", "kinchhau": "Add",
            "rakh": "Add", "rakhyo": "Add",
            "aayo": "Add", "aaucha": "Add",
            "add": "Add", "increase": "Add", "bought": "Add",

            # ── CHECK — query current stock level ────────────────────────────
            # Devanagari
            "बाँकी": "Check", "बाँकि": "Check",
            "कति": "Check", "कतिवटा": "Check", "कतिओटा": "Check",
            "चेक": "Check", "स्टक": "Check",
            # Romanized
            "banki": "Check", "baaki": "Check", "baki": "Check",
            "kati": "Check", "katiwata": "Check",
            "check": "Check", "stock": "Check",
            "how much": "Check", "how many": "Check",
        }

        # ── Step 1: Normalise punctuation ──────────────────────────────────────
        # Remove Devanagari daṇḍa, periods, commas — they confuse the LLM
        text = text.replace("।", " ").replace(".", " ").replace(",", " ")

        # ── Step 2: Lowercase a working copy for Romanized matches ────────────
        # We do case-insensitive replacement by lowercasing text temporarily,
        # then applying canonical (properly cased) tokens.
        # Strategy: work on lowercased text so Romanized variants match regardless
        # of Whisper capitalisation.
        lowered = text.lower()

        # ── Step 3: Apply corrections longest-key-first to avoid partial hits ──
        # e.g. "paanch" must be replaced before "pan" or "cha"
        for bad_word in sorted(corrections.keys(), key=len, reverse=True):
            good_word = corrections[bad_word]
            # Replace in original text (for Devanagari, exact match)
            text = text.replace(bad_word, f" {good_word} ")
            # Replace in lowercased text (for Romanized variants)
            lowered = lowered.replace(bad_word.lower(), f" {good_word.lower()} ")

        # ── Step 4: Reconcile — for each Romanized canonical token in lowered,
        #            inject the properly-cased version into text ─────────────────
        canonical_tokens = {
            "rice", "lentils", "salt", "sugar", "oil", "flour",
            "turmeric", "eggs", "beaten_rice", "biscuits",
            "add", "remove", "check",
            "kg", "pieces", "packet", "liter",
        }
        words_in_lowered = lowered.split()
        words_in_text   = text.split()

        # Rebuild from lowered (which has all replacements) — capitalise items & actions
        final_words = []
        for w in words_in_lowered:
            clean = w.strip()
            if clean in {"rice","lentils","salt","sugar","oil","flour",
                         "turmeric","eggs","beaten_rice","biscuits"}:
                final_words.append(clean.capitalize() if "_" not in clean else "Beaten_Rice")
            elif clean in {"add","remove","check"}:
                final_words.append(clean.capitalize())
            elif clean.isdigit() or clean in {"kg","pieces","packet","liter"}:
                final_words.append(clean)
            else:
                final_words.append(clean)

        cleaned_text = " ".join(final_words)

        # ── Step 5: Clean up extra whitespace ─────────────────────────────────
        cleaned_text = " ".join(cleaned_text.split())

        return cleaned_text

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe Nepali audio and return a pre-cleaned English-token string.

        The initial_prompt biases Whisper toward the vocabulary we care about,
        reducing hallucinations of random Hindi/Sanskrit words.
        """
        # Prompt contains both Devanagari and Romanized versions of every key word
        # so Whisper's language model is primed before it hears a single audio frame.
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
            condition_on_previous_text=False,   # prevent hallucination loops
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
        )

        raw_text = result["text"].strip()
        if len(raw_text) < 2:
            return ""

        cleaned_text = self._apply_brute_force_corrections(raw_text)
        print(f"🛠️  RAW      : {raw_text!r}")
        print(f"✅  CLEANED  : {cleaned_text!r}")

        return cleaned_text