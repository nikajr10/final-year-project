import whisper
import torch

class WhisperService:
    def __init__(self):
        # "medium" is the best balance for Nepali. 
        # It downloads about 1.5GB the first time you run it.
        print("⏳ Loading Whisper Model... (This may take time)")
        self.model = whisper.load_model("medium")
        print("✅ Whisper Model Loaded!")

    def transcribe(self, audio_path: str):
        """
        Step 2: OpenAI Whisper (ASR).
        Converts 16kHz WAV -> Nepali Text.
        """
        try:
            # We explicitly tell it to expect Nepali ('ne')
            result = self.model.transcribe(audio_path, language='ne')
            return result['text']
        except Exception as e:
            print(f"❌ Whisper Error: {e}")
            return None

# --- Quick Test Block ---
if __name__ == "__main__":
    # Test with the file you just cleaned!
    # Update this filename to match what your terminal just outputted
    test_path = "data/processed/vad_person_5_Nun ghatau far.wav.wav" 
    
    service = WhisperService()
    text = service.transcribe(test_path)
    
    print(f"\n🗣️ Transcription: {text}")