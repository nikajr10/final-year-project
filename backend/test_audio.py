import os
from app.core.audio_processor import AudioProcessor

# Setup paths (Use absolute paths to be safe)
base_dir = os.path.dirname(os.path.abspath(__file__))
raw_folder = os.path.join(base_dir, "data", "raw")
processed_folder = os.path.join(base_dir, "data", "processed")

# Ensure processed folder exists
os.makedirs(processed_folder, exist_ok=True)

# Create processor
processor = AudioProcessor()

# 1. AUTO-DETECT FILENAME
# Instead of hardcoding "13 Feb...", let's pick the first file in the folder automatically
try:
    files = [f for f in os.listdir(raw_folder) if not f.startswith('.')]
    if not files:
        print("❌ No files found in data/raw!")
        exit()
    test_file = files[0] # Pick the first file found
except FileNotFoundError:
    print(f"❌ Folder not found: {raw_folder}")
    exit()

print(f"📂 Found file: {test_file}")

input_path = os.path.join(raw_folder, test_file)
clean_path = os.path.join(processed_folder, "clean_" + test_file + ".wav") # Add .wav extension explicitly
final_vad_path = os.path.join(processed_folder, "vad_" + test_file + ".wav")

print(f"Processing...")

# Step 1: Clean & Convert
if processor.convert_and_clean(input_path, clean_path):
    print("✅ Step 1: FFmpeg Cleaned Success!")
else:
    print("❌ Step 1 Failed.")
    exit()

# Step 2: Remove Silence
try:
    processor.remove_silence(clean_path, final_vad_path)
    print("✅ Step 2: WebRTC Silence Removal Success!")
    print(f"🎉 Output saved to: {final_vad_path}")
except Exception as e:
    print(f"❌ Step 2 Failed: {e}")