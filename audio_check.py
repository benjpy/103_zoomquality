
import numpy as np
import os
from pydub import AudioSegment
import av
import threading
import io

class AudioRecorder:
    def __init__(self):
        self.frames_lock = threading.Lock()
        self.frames = []
        
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        with self.frames_lock:
            self.frames.append(frame)
        return frame
        
    def export(self, output_path):
        """
        Exports recorded frames to a WAV file.
        """
        with self.frames_lock:
            frames = self.frames.copy()
            
        if not frames:
            return None
            
        # Combine all frames
        # Assuming all frames have same rate/channels
        
        # Method: Convert each av.AudioFrame to bytes and stick them together?
        # Better: Uses pydub or av container to write.
        
        # Let's use pydub to construct from raw bytes provided by av
        # av.AudioFrame.to_ndarray() returns numpy array
        
        output_data = io.BytesIO()
        container = av.open(output_data, mode='w', format='wav')
        stream = container.add_stream('pcm_s16le', rate=frames[0].rate)
        stream.layout = str(frames[0].layout.name) # e.g. 'stereo' or 'mono'
        
        for frame in frames:
            for packet in stream.encode(frame):
                container.mux(packet)
                
        # Flush
        for packet in stream.encode():
            container.mux(packet)
            
        container.close()
        output_data.seek(0)
        
        # Write to file
        with open(output_path, 'wb') as f:
            f.write(output_data.getvalue())
            
        return output_path

def analyze_audio_file(audio_path):
    """
    Analyzes an audio file (WAV/WEBM) for quality metrics.
    """
    try:
        # Load audio file
        audio = AudioSegment.from_file(audio_path)
        
        # Convert to mono and get raw data
        audio = audio.set_channels(1)
        samples = np.array(audio.get_array_of_samples())
        
        # If empty
        if len(samples) == 0:
            return {"error": "Empty audio file"}
            
        samplerate = audio.frame_rate
        
        # Audio Analysis Logic
        
        # 1. RMS & dB
        samples_float = samples.astype(np.float64)
        max_possible_val = (2 ** (audio.sample_width * 8 - 1)) if audio.sample_width < 4 else 1.0 # Rough approx
        # For simplicity, just use standard int16 max
        if audio.sample_width == 2:
            max_possible_val = 32768.0
        elif audio.sample_width == 4:
            max_possible_val = 2147483648.0
        else:
            max_possible_val = 32768.0
            
        rms = np.sqrt(np.mean(samples_float**2))
        
        # dBFS
        db = 20 * np.log10(rms / max_possible_val + 1e-9)
        
        # Peak
        peak = np.max(np.abs(samples_float))
        
        # 2. Noise Floor & SNR
        chunk_len_ms = 100
        chunk_size = int(samplerate * (chunk_len_ms / 1000))
        
        # Pad and reshape
        pad_length = chunk_size - (len(samples_float) % chunk_size)
        if pad_length < chunk_size:
            samples_padded = np.pad(samples_float, (0, pad_length))
        else:
            samples_padded = samples_float
            
        chunks = samples_padded.reshape(-1, chunk_size)
        if len(chunks) > 0:
            chunk_rms = np.sqrt(np.mean(chunks**2, axis=1))
            sorted_rms = np.sort(chunk_rms)
            
            # Noise floor (quietest 10%)
            noise_floor_rms = np.mean(sorted_rms[:max(1, int(len(sorted_rms) * 0.1))])
            noise_floor_db = 20 * np.log10(noise_floor_rms / max_possible_val + 1e-9)
            
            # Signal (loudest 50%)
            signal_rms = np.mean(sorted_rms[int(len(sorted_rms) * 0.5):])
            signal_db = 20 * np.log10(signal_rms / max_possible_val + 1e-9)
            
            snr_db = signal_db - noise_floor_db
        else:
            noise_floor_db = -90
            snr_db = 0
            
        return {
            "rms_amplitude": rms,
            "decibels": db,
            "peak_amplitude": peak,
            "noise_floor_db": noise_floor_db,
            "snr_db": snr_db,
            "audio_path": audio_path,
            "duration_sec": len(audio) / 1000.0
        }
        
    except Exception as e:
        return {"error": str(e)}
