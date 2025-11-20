import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import os

def list_input_devices():
    """
    Returns a list of input devices (index, name).
    """
    devices = sd.query_devices()
    input_devices = []
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            input_devices.append((i, dev['name']))
    return input_devices

def check_audio_quality(duration=5, samplerate=44100, output_file="test_audio.wav", device_index=None):
    """
    Records audio, identifies source, saves to file, and analyzes quality.
    """
    print(f"Starting audio check for {duration} seconds... Please speak normally.")
    
    try:
        # Get device info
        if device_index is not None:
            device_info = sd.query_devices(device_index, kind='input')
        else:
            device_info = sd.query_devices(kind='input')
            
        device_name = device_info['name']
        print(f"Using Microphone: {device_name}")
        
        # Record audio
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float64', device=device_index)
        sd.wait()
        
        # Save to file (convert to 16-bit PCM)
        wav_data = (recording * 32767).astype(np.int16)
        wav.write(output_file, samplerate, wav_data)
        
        # Flatten the array for analysis
        audio_data = recording.flatten()
        
        # Calculate RMS (Root Mean Square) Amplitude
        rms = np.sqrt(np.mean(audio_data**2))
        
        # Convert to Decibels (dB)
        db = 20 * np.log10(rms + 1e-9)
        
        # Peak amplitude
        peak = np.max(np.abs(audio_data))
        
        # Noise Floor & SNR Calculation
        # Split into small chunks (e.g., 100ms) to find silent parts
        chunk_size = int(samplerate * 0.1)
        # Pad if needed to make divisible
        pad_length = chunk_size - (len(audio_data) % chunk_size)
        if pad_length < chunk_size:
            audio_padded = np.pad(audio_data, (0, pad_length))
        else:
            audio_padded = audio_data
            
        chunks = audio_padded.reshape(-1, chunk_size)
        chunk_rms = np.sqrt(np.mean(chunks**2, axis=1))
        
        # Assume the quietest 10% of chunks represent the noise floor
        sorted_rms = np.sort(chunk_rms)
        noise_floor_rms = np.mean(sorted_rms[:max(1, int(len(sorted_rms) * 0.1))])
        noise_floor_db = 20 * np.log10(noise_floor_rms + 1e-9)
        
        # Signal to Noise Ratio
        # Signal is the RMS of the whole clip (or maybe the loud parts, but whole clip RMS is standard simple metric)
        # Better: Signal = Average of top 50% loudest chunks
        signal_rms = np.mean(sorted_rms[int(len(sorted_rms) * 0.5):])
        signal_db = 20 * np.log10(signal_rms + 1e-9)
        
        snr_db = signal_db - noise_floor_db
        
        return {
            "rms_amplitude": rms,
            "decibels": db,
            "peak_amplitude": peak,
            "noise_floor_db": noise_floor_db,
            "snr_db": snr_db,
            "device_name": device_name,
            "audio_path": os.path.abspath(output_file)
        }
        
    except Exception as e:
        return {"error": str(e)}

def play_audio(file_path):
    """
    Plays back the recorded audio file.
    """
    try:
        samplerate, data = wav.read(file_path)
        sd.play(data, samplerate)
        sd.wait()
    except Exception as e:
        print(f"Error playing audio: {e}")

if __name__ == "__main__":
    # Test run
    results = check_audio_quality()
    print(results)
    if "audio_path" in results:
        print("Playing back...")
        play_audio(results["audio_path"])
