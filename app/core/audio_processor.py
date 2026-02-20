import os
import subprocess
import webrtcvad
import contextlib
import wave
import collections

class AudioProcessor:
    def __init__(self):
        # 0 is least aggressive, 3 is most aggressive (filters out breathing/noise)
        self.vad = webrtcvad.Vad(2) 

    def convert_and_clean(self, input_path: str, output_path: str):
        """
        Step 1: FFmpeg Normalization & High-Pass Filter.
        """
        # 1. Check if input file actually exists before running FFmpeg
        if not os.path.exists(input_path):
            print(f"❌ Error: Input file not found at: {input_path}")
            return False

        try:
            command = [
                'ffmpeg',
                '-y',                     # Overwrite output file
                '-i', input_path,         # Input file
                '-af', 'highpass=f=200,loudnorm', # REMOVED SPACE here (Critical Fix)
                '-ar', '16000',           # Convert to 16kHz
                '-ac', '1',               # Convert to Mono
                '-c:a', 'pcm_s16le',      # Codec: PCM 16-bit
                output_path
            ]
            
            # Run command. If it fails, we capture the output to see WHY.
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ FFmpeg Error: {result.stderr}") # Print the actual error from FFmpeg
                return False
                
            return True
        except Exception as e:
            print(f"❌ Python Error: {e}")
            return False

    def remove_silence(self, audio_path: str, output_path: str):
        """
        Step 2: WebRTC VAD (Voice Activity Detection).
        Reads the 16kHz WAV file, detects voice frames, and removes silence.
        """
        sample_rate = 16000
        frame_duration_ms = 30  # WebRTC checks audio in 30ms chunks
        padding_duration_ms = 300 # Keep a little buffer around speech so it sounds natural
        
        audio, sample_rate = self._read_wave(audio_path)
        frames = self._frame_generator(frame_duration_ms, audio, sample_rate)
        frames = list(frames)
        
        segments = self._vad_collector(sample_rate, frame_duration_ms, padding_duration_ms, self.vad, frames)

        # Combine all speech segments back into a single byte array
        concatenated_audio = b''.join([segment for segment in segments])

        # Write the final voice-only file
        self._write_wave(output_path, concatenated_audio, sample_rate)

    # --- HELPER FUNCTIONS (The Math for VAD) ---

    def _read_wave(self, path):
        with contextlib.closing(wave.open(path, 'rb')) as wf:
            num_channels = wf.getnchannels()
            assert num_channels == 1
            sample_width = wf.getsampwidth()
            assert sample_width == 2
            sample_rate = wf.getframerate()
            assert sample_rate in (8000, 16000, 32000, 48000)
            pcm_data = wf.readframes(wf.getnframes())
            return pcm_data, sample_rate

    def _write_wave(self, path, audio, sample_rate):
        with contextlib.closing(wave.open(path, 'wb')) as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio)

    class Frame(object):
        def __init__(self, bytes, timestamp, duration):
            self.bytes = bytes
            self.timestamp = timestamp
            self.duration = duration

    def _frame_generator(self, frame_duration_ms, audio, sample_rate):
        n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
        offset = 0
        timestamp = 0.0
        duration = (float(n) / sample_rate) / 2.0
        while offset + n < len(audio):
            yield self.Frame(audio[offset:offset + n], timestamp, duration)
            timestamp += duration
            offset += n

    def _vad_collector(self, sample_rate, frame_duration_ms, padding_duration_ms, vad, frames):
        """Filters out non-voiced audio frames."""
        num_padding_frames = int(padding_duration_ms / frame_duration_ms)
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False
        voiced_frames = []

        for frame in frames:
            is_speech = vad.is_speech(frame.bytes, sample_rate)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                if num_voiced > 0.9 * ring_buffer.maxlen:
                    triggered = True
                    for f, s in ring_buffer:
                        voiced_frames.append(f.bytes)
                    ring_buffer.clear()
            else:
                voiced_frames.append(frame.bytes)
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                if num_unvoiced > 0.9 * ring_buffer.maxlen:
                    triggered = False
                    yield b''.join(voiced_frames)
                    ring_buffer.clear()
                    voiced_frames = []
        
        if triggered:
            yield b''.join(voiced_frames)
        elif voiced_frames:
             yield b''.join(voiced_frames)