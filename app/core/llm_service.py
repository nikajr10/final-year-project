import requests
import json
import re

class LLMService:
    def __init__(self):
        # Ollama runs on port 11434 by default
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "llama3"
        
        # 1. THE 10 GOLDEN ITEMS (Strict Enforcement)
        self.valid_items = [
            "Chamal", "Daal", "Tel", "Chini", "Nun", 
            "Chiura", "Maida", "Anda", "Besar", "Biskut"
        ]

    def process_text(self, text: str):
        """
        Step 3: Intelligence Layer (Llama 3)
        Input: "Chamal ek kilo thap"
        Output: {'intent': 'ADD', 'item': 'Chamal', 'qty': 1.0, 'unit': 'kg'}
        """
        
        # --- THE FINAL YEAR PROJECT "BRAIN" ---
        # We explicitly map every possible accent and command from your image.
        system_prompt = f"""
        You are the backend AI for 'SmartBiz', a Nepali Inventory System.
        
        YOUR GOAL: 
        Convert Nepali voice commands into structured JSON data.
        
        ---------------------------------------------------------
        STEP 1: PHONETIC CORRECTION (Fix Accents)
        The user has a Nepali accent. You MUST correct these sounds:
        - "Ryce", "Chammal", "Samal" -> CORRECTION: "Chamal"
        - "Dal", "Daal", "Daal"       -> CORRECTION: "Daal"
        - "Tell", "Tail", "Oil"       -> CORRECTION: "Tel"
        - "Sini", "Cheeni", "Sugar"   -> CORRECTION: "Chini"
        - "Noon", "Namak", "Salt"     -> CORRECTION: "Nun"
        - "Chiura", "Beaten Rice"     -> CORRECTION: "Chiura"
        - "Maida", "Flour"            -> CORRECTION: "Maida"
        - "Anda", "Egg", "Anda"       -> CORRECTION: "Anda"
        - "Vesar", "Besar", "Turmeric"-> CORRECTION: "Besar"
        - "Biscuit", "Biskut"         -> CORRECTION: "Biskut"

        ---------------------------------------------------------
        STEP 2: ITEM MAPPING (Strict)
        Map the corrected word to exactly one of these 10 IDs:
        {self.valid_items}

        ---------------------------------------------------------
        STEP 3: INTENT CLASSIFICATION (Based on Verbs)
        Look for these specific Nepali keywords:
        
        [ADD TO STOCK]
        - Keywords: "thap" (Add), "kinyo" (Bought), "aayo" (Came), "lyayo" (Brought), "rakh" (Put)
        - Action: "ADD"
        
        [REMOVE FROM STOCK]
        - Keywords: "bech" (Sell), "ghata" (Reduce), "gayo" (Went), "deu" (Give)
        - Action: "REMOVE"
        
        [CHECK STOCK]
        - Keywords: "kati cha", "kati banki cha", "stock kati", "check"
        - Action: "CHECK"

        ---------------------------------------------------------
        STEP 4: QUANTITY & UNIT EXTRACTION
        - Convert Nepali numbers to English (e.g., "ek"->1, "dui"->2, "paanch"->5, "das"->10, "pandra"->15, "bis"->20, "pachis"->25).
        - Units:
          - "kilo", "kg" -> "kg"
          - "wata", "piece", "ota" -> "piece"
          - "packet", "poka" -> "packet"
          - "litre", "l" -> "litre"

        ---------------------------------------------------------
        EXAMPLES (Strictly follow this pattern):

        Input: "Chamal ek kilo thap"
        Output: {{"intent": "ADD", "item": "Chamal", "qty": 1.0, "unit": "kg"}}

        Input: "Nun dui packet bech"
        Output: {{"intent": "REMOVE", "item": "Nun", "qty": 2.0, "unit": "packet"}}

        Input: "Besar pachis kilo ghata"
        Output: {{"intent": "REMOVE", "item": "Besar", "qty": 25.0, "unit": "kg"}}

        Input: "Anda pandra wata thap"
        Output: {{"intent": "ADD", "item": "Anda", "qty": 15.0, "unit": "piece"}}

        Input: "Chini kati banki cha"
        Output: {{"intent": "CHECK", "item": "Chini", "qty": 0, "unit": "check"}}

        ---------------------------------------------------------
        FINAL OUTPUT REQUIREMENT:
        Return ONLY valid JSON. No explanations.
        """

        # Prepare the request for Ollama
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\nUser Input: '{text}'\nOutput JSON:",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1  # Very low temperature = Strict & Deterministic (No creativity)
            }
        }

        try:
            print(f"\n🧠 Brain is processing: '{text}'")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            
            result_text = response.json().get('response', '')
            data = json.loads(result_text)
            
            # --- PYTHON SAFETY LAYER (Double Check) ---
            # 1. Ensure Qty is a float
            if 'qty' in data:
                try:
                    data['qty'] = float(data['qty'])
                except:
                    data['qty'] = 0.0
            else:
                data['qty'] = 0.0

            # 2. Ensure Intent is Valid
            if data.get('intent') not in ['ADD', 'REMOVE', 'CHECK']:
                data['intent'] = 'ADD' # Default fallback

            return data

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return None