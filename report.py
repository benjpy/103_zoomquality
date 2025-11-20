def get_rating(value, thresholds):
    """
    Generic function to get a rating based on thresholds.
    thresholds: dict with keys 'excellent', 'good', 'fair' (implied poor if below fair)
    """
    if value >= thresholds['excellent']:
        return "Excellent"
    elif value >= thresholds['good']:
        return "Good"
    elif value >= thresholds['fair']:
        return "Fair"
    else:
        return "Poor"

def analyze_video_results(results):
    if "error" in results:
        return "Error", ["Could not access camera. Check permissions."]
    
    brightness = results.get("avg_brightness", 0)
    sharpness = results.get("avg_sharpness", 0)
    
    recommendations = []
    
    # Brightness Analysis
    # Recalibrated: User found 117 "plenty of light".
    # Broaden the "Good" range significantly.
    if brightness < 40:
        recommendations.append("Your video is too dark. Turn on a light or face a window.")
        b_rating = "Poor"
    elif brightness > 230:
        recommendations.append("Your video is too bright/washed out. Reduce lighting.")
        b_rating = "Fair"
    else:
        b_rating = "Excellent"
        
    # Sharpness Analysis
    # User found 280 "fine".
    if sharpness < 50:
        recommendations.append("Your video is blurry. Clean your lens or adjust focus.")
        s_rating = "Poor"
    elif sharpness < 100:
        recommendations.append("Video is slightly soft. Ensure you are in focus.")
        s_rating = "Fair"
    else:
        s_rating = "Excellent"
        
    # Face & Framing Analysis
    f_rating = "Excellent"
    if results.get("face_detected"):
        headroom = results.get("avg_headroom", 20)
        face_bright = results.get("avg_face_brightness", 100)
        face_prop = results.get("avg_face_prop", 0.4)
        
        # Headroom: Ideal is around 10-20%
        if headroom < 5:
            recommendations.append("Not enough headroom. Tilt camera up.")
            f_rating = "Fair"
        elif headroom > 35: # Relaxed from 30
            recommendations.append("Too much headroom. Tilt camera down or sit taller.")
            f_rating = "Fair"
            
        # Face Proportion
        if face_prop < 0.20: # Relaxed from 0.25
            recommendations.append("You are too far from the camera. Move closer.")
            if f_rating != "Poor": f_rating = "Fair"
            
        # Face Brightness
        if face_bright < 40: # Relaxed from 70
            recommendations.append("Your face is too dark. Add front lighting.")
            f_rating = "Poor"
    else:
        recommendations.append("No face detected. Center yourself in the frame.")
        f_rating = "Fair"

    # Overall Video Rating
    if "Poor" in [b_rating, s_rating, f_rating]:
        overall = "Poor"
    elif "Fair" in [b_rating, s_rating, f_rating]:
        overall = "Fair"
    else:
        overall = "Excellent"
        
    return overall, recommendations

def analyze_audio_results(results):
    if "error" in results:
        return "Error", ["Could not access microphone. Check permissions."]
        
    db = results.get("decibels", -100)
    snr = results.get("snr_db", 20)
    
    recommendations = []
    
    # Volume Analysis
    # Recalibrated: User found -43dB "perfectly audible".
    # Further relaxed: -50dB is now "Fair".
    
    if db < -65:
        recommendations.append("Your microphone volume is very low. Speak up or move closer.")
        rating = "Poor"
    elif db < -55: # Was -60
        recommendations.append("Audio is a bit quiet, but audible.")
        rating = "Fair"
    elif db > -5:
        recommendations.append("Audio might be clipping (too loud). Move back slightly.")
        rating = "Fair"
    else:
        rating = "Excellent"
        
    # Noise Analysis
    if snr < 10:
        recommendations.append("High background noise detected (Low SNR). Use a headset or find a quiet room.")
        if rating == "Excellent": rating = "Good"
    elif snr < 20:
        recommendations.append("Some background noise detected. SNR (Signal-to-Noise Ratio) should be higher (>20dB).")
        
    return rating, recommendations

def analyze_network_results(results):
    if "error" in results:
        return "Error", ["Could not run speed test. Check internet connection."]
        
    down = results.get("download_mbps", 0)
    up = results.get("upload_mbps", 0)
    ping = results.get("ping_ms", 999)
    
    recommendations = []
    
    # Zoom HD requirements: 3.0 Mbps up/down
    if up < 1.0 or down < 1.0:
        recommendations.append("Internet speed is very slow. Video may freeze.")
        rating = "Poor"
    elif up < 3.0 or down < 3.0:
        recommendations.append("Internet is okay for standard calls, but HD may struggle.")
        rating = "Fair"
    else:
        rating = "Excellent"
        
    if ping > 100:
        recommendations.append("High latency detected. There may be delays in conversation.")
        if rating != "Poor": rating = "Fair"
        
    return rating, recommendations
