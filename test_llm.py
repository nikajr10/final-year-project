from app.core.llm_service import LLMService

def test_intelligence():
    print("🚀 STARTING FINAL YEAR PROJECT INTELLIGENCE TEST...\n")
    service = LLMService()

    # --- TEST SUITE 1: PHONETIC CORRECTION (The "Accent" Test) ---
    print("🧪 SUITE 1: PHONETIC CORRECTION (Fixing Accents)")
    
    # Test 1: "Ryce" -> Chamal
    input_1 = "Ryce das kilo thap"
    print(f"   Input: '{input_1}'")
    result_1 = service.process_text(input_1)
    print(f"   🤖 Result: {result_1}")
    
    if result_1 and result_1.get('item') == 'Chamal':
        print("   ✅ SUCCESS: 'Ryce' corrected to 'Chamal'")
    else:
        print("   ❌ FAILED: Accent correction missed.")
    print("-" * 40)

    # Test 2: "Namak" -> Nun
    input_2 = "Namak paanch packet bech"
    print(f"   Input: '{input_2}'")
    result_2 = service.process_text(input_2)
    print(f"   🤖 Result: {result_2}")

    if result_2 and result_2.get('item') == 'Nun':
        print("   ✅ SUCCESS: 'Namak' mapped to 'Nun'")
    else:
        print("   ❌ FAILED: Hindi mapping missed.")
    print("-" * 40)


    # --- TEST SUITE 2: COMMAND MAPPING (The "Verb" Test) ---
    print("\n🧪 SUITE 2: NEPALI COMMAND MAPPING (Verbs)")

    # Test 3: "Thap" -> ADD
    input_3 = "Chini ek kilo thap"
    print(f"   Input: '{input_3}'")
    result_3 = service.process_text(input_3)
    
    if result_3 and result_3.get('intent') == 'ADD':
        print(f"   ✅ SUCCESS: 'thap' recognized as ADD")
    else:
        print(f"   ❌ FAILED: 'thap' not recognized. Got: {result_3.get('intent')}")
    print("-" * 40)

    # Test 4: "Ghata" -> REMOVE
    input_4 = "Tel ek litre ghata"
    print(f"   Input: '{input_4}'")
    result_4 = service.process_text(input_4)

    if result_4 and result_4.get('intent') == 'REMOVE':
        print(f"   ✅ SUCCESS: 'ghata' recognized as REMOVE")
    else:
        print(f"   ❌ FAILED: 'ghata' not recognized. Got: {result_4.get('intent')}")
    print("-" * 40)

    # Test 5: "Kati banki cha" -> CHECK (Optional feature)
    input_5 = "Daal kati banki cha"
    print(f"   Input: '{input_5}'")
    result_5 = service.process_text(input_5)

    if result_5 and result_5.get('intent') == 'CHECK':
        print(f"   ✅ SUCCESS: 'kati banki cha' recognized as CHECK")
    else:
        print(f"   ❌ FAILED: Stock check failed. Got: {result_5.get('intent')}")


    # --- FINAL VERDICT ---
    print("\n🏁 TEST COMPLETE. If you see all ✅, your AI Brain is 100% Ready.")

if __name__ == "__main__":
    test_intelligence()