import streamlit as st
import cv2
import numpy as np
import time
import os
from video_check import check_video_quality, draw_guide
from audio_check import check_audio_quality, list_input_devices
from network_check import check_network_quality
from report import analyze_video_results, analyze_audio_results, analyze_network_results

st.set_page_config(page_title="Video Call Quality Checker", page_icon="📹", layout="wide")

def get_star_rating(value, min_val, max_val, inverse=False):
    """
    Convert a value to a 1-5 star string.
    """
    if value is None: return "N/A"
    
    # Normalize to 0-1
    if inverse:
        norm = 1 - ((value - min_val) / (max_val - min_val))
    else:
        norm = (value - min_val) / (max_val - min_val)
        
    norm = max(0, min(1, norm))
    stars = int(norm * 5)
    if stars == 0 and norm > 0: stars = 1 # At least 1 star if not 0
    
    return "⭐" * stars + "☆" * (5 - stars)

import requests
import datetime

def get_location():
    try:
        response = requests.get("http://ip-api.com/json/")
        if response.status_code == 200:
            data = response.json()
            return f"{data.get('city')}, {data.get('country')}"
    except:
        return "Unknown Location"
    return "Unknown Location"

st.title("📹 Video Call Quality Checker")
st.markdown("Analyze your setup for Zoom, Teams, Meet, etc.")

# Header Info (Time & Location)
col_h1, col_h2 = st.columns(2)
with col_h1:
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"🕒 Local Time: {current_time}")
with col_h2:
    location = get_location()
    st.caption(f"📍 Location: {location}")

if 'results' not in st.session_state:
    st.session_state.results = {}

with st.sidebar:
    st.header("Settings")
    
    # Audio Device Selection
    input_devices = list_input_devices()
    device_names = [d[1] for d in input_devices]
    selected_device_name = st.selectbox("Microphone", device_names)
    selected_device_index = next((d[0] for d in input_devices if d[1] == selected_device_name), None)
    
    # Defaults
    video_duration = 2
    audio_duration = 5
    
    # Initialize Session State for Workflow
    if 'workflow_state' not in st.session_state:
        st.session_state.workflow_state = 'idle' # idle, preview, analyzing
        
    # --- Workflow Control ---
    if st.session_state.workflow_state == 'idle':
        if st.button("Start Analysis", type="primary"):
            st.session_state.workflow_state = 'preview'
            st.rerun()
            
    elif st.session_state.workflow_state == 'preview':
        st.info("Adjust your position. Click **Capture Photo** when ready.")
        
        col_p1, col_p2 = st.columns([1, 3])
        with col_p1:
            if st.button("Capture Photo", type="primary"):
                st.session_state.workflow_state = 'analyzing'
                st.rerun()
        with col_p2:
             if st.button("Cancel"):
                 st.session_state.workflow_state = 'idle'
                 st.rerun()
        
        # Preview Loop
        preview_placeholder = st.empty()
        cap = cv2.VideoCapture(0)
        
        from video_check import draw_guide
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    st.error("Camera not accessible.")
                    break
                
                # Resize for consistency
                height, width = frame.shape[:2]
                max_width = 640
                if width > max_width:
                    scale = max_width / width
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (max_width, new_height))
                    
                draw_guide(frame)
                
                # Convert to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                preview_placeholder.image(frame_rgb, channels="RGB")
                
                # Small sleep to prevent CPU hogging
                time.sleep(0.03)
        finally:
            cap.release()
            
    elif st.session_state.workflow_state == 'analyzing':
        st.session_state.running = True
        
        # 1. Video Check
        st.toast("Starting Video Check...", icon="📷")
        
        video_placeholder = st.empty()
        
        def update_video_frame(frame):
            # Convert BGR to RGB for Streamlit
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB")
            return False # Don't stop
            
        # Run Video Check (Countdown + Capture)
        # We pass on_frame to render the countdown in Streamlit
        video_res = check_video_quality(duration=video_duration, on_frame=update_video_frame)
        
        if "error" in video_res:
            st.error(f"Video Check Failed: {video_res['error']}")
            st.session_state.running = False
            st.session_state.workflow_state = 'idle'
            st.stop()
            
        video_placeholder.empty() # Clear video after check
        st.session_state.results['video'] = video_res
        
        # 2. Audio Check
        audio_msg = st.empty()
        audio_msg.info("Get ready for Audio Check...")
        time.sleep(1)
        for i in range(3, 0, -1):
            audio_msg.markdown(f"### Recording in {i}...")
            time.sleep(1)
        audio_msg.markdown("### 🎙️ Speak now!")
        
        audio_res = check_audio_quality(duration=audio_duration, device_index=selected_device_index)
        audio_msg.empty() # Clear message
        st.session_state.results['audio'] = audio_res
        
        # 3. Network Check
        st.toast("Checking Network...", icon="🌐")
        network_res = check_network_quality()
        st.session_state.results['network'] = network_res
        
        st.session_state.running = False
        st.session_state.workflow_state = 'idle' # Reset for next time
        st.success("Analysis Complete!")
        st.rerun() # Rerun to update time and layout

if 'video' in st.session_state.results:
    res = st.session_state.results
    
    # Analyze
    v_rating, v_recs = analyze_video_results(res['video'])
    a_rating, a_recs = analyze_audio_results(res['audio'])
    n_rating, n_recs = analyze_network_results(res['network'])
    
    # Display Dashboard
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Video")
        
        # Recommendations at Very Top
        if v_recs:
            for rec in v_recs:
                st.warning(rec, icon="⚠️")
        else:
            st.success("Video looks good!", icon="✅")
            
        st.metric("Rating", v_rating)
        st.divider()

        # Display Last Frame directly from memory
        if "last_frame" in res['video'] and res['video']['last_frame'] is not None:
            st.image(res['video']['last_frame'], caption=f"Captured at {datetime.datetime.now().strftime('%H:%M:%S')}")
        elif "photo_path" in res['video']:
             st.image(res['video']['photo_path'], caption="Captured Frame (File)")

        # Metrics with Stars
        b_val = res['video'].get('avg_brightness', 0)
        s_val = res['video'].get('avg_sharpness', 0)
        
        # Recalibrated ranges based on user feedback
        st.write(f"**Brightness:** {get_star_rating(b_val, 40, 130)} ({b_val:.1f}) `Target: >40`")
        st.write(f"**Sharpness:** {get_star_rating(s_val, 50, 300)} ({s_val:.1f}) `Target: >50`")
        
        if res['video'].get('face_detected'):
            h_val = res['video'].get('avg_headroom', 0)
            fb_val = res['video'].get('avg_face_brightness', 0)
            fp_val = res['video'].get('avg_face_prop', 0)
            
            # Headroom ideal is ~15%. Deviation from 15 is bad.
            h_score = 100 - abs(h_val - 15) * 3 
            st.write(f"**Headroom:** {get_star_rating(h_score, 0, 100)} ({h_val:.1f}%) `Target: ~15%`", help="Percentage of screen height above your head.")
            
            # Face Proportion: Ideal > 0.3
            st.write(f"**Face Size:** {get_star_rating(fp_val, 0.2, 0.5)} ({(fp_val*100):.1f}%) `Target: 20-50%`")
            st.write(f"**Face Brightness:** {get_star_rating(fb_val, 30, 130)} ({fb_val:.1f}) `Target: >40`")
        else:
            st.warning("No face detected.")
            
    with col2:
        st.subheader("Audio")
        
        # Recommendations at Very Top
        if a_recs:
            for rec in a_recs:
                st.warning(rec, icon="⚠️")
        else:
            st.success("Audio sounds clear!", icon="✅")
            
        st.metric("Rating", a_rating)
        st.divider()

        st.write(f"**Source:** {res['audio'].get('device_name', 'Unknown')}")
        
        vol_val = res['audio'].get('decibels', -100)
        snr_val = res['audio'].get('snr_db', 0)
        
        # Recalibrated Volume: -70 to -35
        st.write(f"**Volume:** {get_star_rating(vol_val, -70, -35)} ({vol_val:.1f} dB) `Target: >-65 dB`")
        st.write(f"**Noise (SNR):** {get_star_rating(snr_val, 10, 50)} ({snr_val:.1f} dB) `Target: >20 dB`")
        
        if "audio_path" in res['audio']:
            st.audio(res['audio']['audio_path'])
            
    with col3:
        st.subheader("Network")
        
        # Recommendations at Very Top
        if n_recs:
            for rec in n_recs:
                st.warning(rec, icon="⚠️")
        else:
            st.success("Network is stable!", icon="✅")
            
        st.metric("Rating", n_rating)
        st.divider()
        
        d_val = res['network'].get('download_mbps', 0)
        u_val = res['network'].get('upload_mbps', 0)
        p_val = res['network'].get('ping_ms', 999)
        
        st.write(f"**Download:** {get_star_rating(d_val, 0, 100)} ({d_val:.1f} Mbps)")
        st.write(f"**Upload:** {get_star_rating(u_val, 0, 20)} ({u_val:.1f} Mbps)")
        st.write(f"**Ping:** {get_star_rating(p_val, 0, 100, inverse=True)} ({p_val:.0f} ms)")

    st.divider()
    
    st.subheader("Recommendations")
    all_recs = v_recs + a_recs + n_recs
    if all_recs:
        for rec in all_recs:
            st.warning(rec)
    else:
        st.success("Everything looks great! You are ready for your call.")

else:
    st.info("Click 'Run Analysis' in the sidebar to start.")
