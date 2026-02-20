import os
import csv
import time
from app.core.audio_processor import AudioProcessor
from app.core.whisper_service import WhisperService

def main():
    # --- CONFIGURATION ---
    raw_folder = "data/raw"
    processed_folder = "data/processed"
    output_csv = "data/dataset_results.csv"
    
    # Ensure processed folder exists
    os.makedirs(processed_folder, exist_ok=True)

    # --- INITIALIZE AI MODELS ---
    print("⏳ Initializing Audio Processor & Whisper AI...")
    processor = AudioProcessor()
    whisper_service = WhisperService()
    print("✅ Models Loaded. Starting Batch Process...")

    # Get list of all files (ignoring hidden files like .DS_Store)
    all_files = [f for f in os.listdir(raw_folder) if not f.startswith('.')]
    total_files = len(all_files)
    
    # Prepare CSV file
    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Filename", "Transcription", "Status"]) # Header

        start_time = time.time()

        # --- THE LOOP ---
        for index, filename in enumerate(all_files):
            input_path = os.path.join(raw_folder, filename)
            
            # Create a safe filename for the cleaned version
            safe_name = filename.replace(" ", "_").replace(",", "") 
            clean_path = os.path.join(processed_folder, f"clean_{safe_name}.wav")

            print(f"[{index + 1}/{total_files}] Processing: {filename}...", end=" ")

            try:
                # 1. CLEAN (FFmpeg)
                # We skip VAD for now to prevent the "Silence" bug you had earlier.
                # Just simple cleaning works best for bulk data.
                if processor.convert_and_clean(input_path, clean_path):
                    
                    # 2. TRANSCRIBE (Whisper)
                    # passing fp16=False to avoid the yellow warning
                    text = whisper_service.model.transcribe(clean_path, language='ne', fp16=False)['text']
                    
                    # 3. SAVE
                    writer.writerow([filename, text.strip(), "Success"])
                    print("✅ Done")
                else:
                    writer.writerow([filename, "", "FFmpeg Failed"])
                    print("❌ Clean Failed")

            except Exception as e:
                writer.writerow([filename, "", f"Error: {str(e)}"])
                print(f"❌ Error: {e}")

            # Flush the file every 10 items so you don't lose data if it crashes
            if index % 10 == 0:
                file.flush()

    duration = (time.time() - start_time) / 60
    print(f"\n🎉 FINISHED! Processed {total_files} files in {duration:.2f} minutes.")
    print(f"📄 Results saved to: {output_csv}")

if __name__ == "__main__":
    main()