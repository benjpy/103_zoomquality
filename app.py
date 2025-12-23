import streamlit as st
import cv2
import numpy as np
import time
import os
import datetime
import requests
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

from video_check import VideoProcessor
from audio_check import AudioRecorder, analyze_audio_file
from network_check import check_network_quality
from report import analyze_video_results, analyze_audio_results, analyze_network_results

# RTC Configuration (STUN servers)
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

st.set_page_config(page_title="Video Call Quality Checker", page_icon="📹", layout="wide")

def get_star_rating(value, min_val, max_val, inverse=False):
    """
    Convert a value to a 1-5 star string.
    """
    if value is None: return "N/A"
    if inverse:
        norm = 1 - ((value - min_val) / (max_val - min_val))
    else:
        norm = (value - min_val) / (max_val - min_val)
    norm = max(0, min(1, norm))
    stars = int(norm * 5)
    if stars == 0 and norm > 0: stars = 1
    return "⭐" * stars + "☆" * (5 - stars)

def get_location():
    try:
        response = requests.get("http://ip-api.com/json/", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return f"{data.get('city')}, {data.get('country')}"
    except:
        return "Unknown Location"
    return "Unknown Location"

st.title("📹 Video Call Quality Checker")
st.markdown("Analyze your setup for Zoom, Teams, Meet, etc.")

# Header Info
col_h1, col_h2 = st.columns(2)
with col_h1:
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"🕒 Local Time: {current_time}")
with col_h2:
    location = get_location()
    st.caption(f"📍 Location: {location}")

if 'results' not in st.session_state:
    st.session_state.results = {}
if 'workflow_state' not in st.session_state:
    st.session_state.workflow_state = 'idle'  # idle, video, audio, network, complete

# --- Sidebar ---
with st.sidebar:
    st.header("Control Panel")
    if st.button("Reset / New Check", type="secondary"):
        st.session_state.results = {}
        st.session_state.workflow_state = 'idle'
        st.rerun()

# --- Main Logic ---

# 1. Start Screen
if st.session_state.workflow_state == 'idle':
    st.info("Click 'Start Analysis' to begin the checks. Browser permission will be requested for Camera and Microphone.")
    if st.button("Start Analysis", type="primary"):
        st.session_state.workflow_state = 'video'
        st.rerun()

# 2. Video Check
elif st.session_state.workflow_state == 'video':
    st.header("Step 1: Video Check")
    st.info("Align your face in the oval. Wait for a few seconds of analysis, then click 'Finish Video Check'.")
    
    ctx = webrtc_streamer(
        key="video-check",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIGURATION,
        video_processor_factory=VideoProcessor,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )
    
    if ctx.video_processor:
        # We can't easily access stats in real-time here without more complex shared state or callbacks update UI.
        # But we can access it when user clicks "Finish"
        pass
        
    if st.button("Finish Video Check", type="primary"):
        if ctx.video_processor:
            stats = ctx.video_processor.get_stats()
            if stats:
                st.session_state.results['video'] = stats
                st.success("Video captured!")
                st.session_state.workflow_state = 'audio'
                st.rerun()
            else:
                st.warning("No video data captured yet. Make sure the video is playing.")
        else:
            st.warning("Please start the video stream first.")

# 3. Audio Check
elif st.session_state.workflow_state == 'audio':
    st.header("Step 2: Audio Check")
    st.info("Click 'Start' on the recorder below. Speak normally for 5 seconds. Then click 'Stop'.")
    
    # Audio recorder
    ctx = webrtc_streamer(
        key="audio-check",
        mode=WebRtcMode.SENDONLY,
        rtc_configuration=RTC_CONFIGURATION,
        audio_processor_factory=AudioRecorder,
        media_stream_constraints={"video": False, "audio": True},
    )
    
    if st.button("Analyze Recorded Audio", type="primary"):
        if ctx.audio_processor:
            # Save to file
            output_file = "recorded_audio.wav"
            saved_path = ctx.audio_processor.export(output_file)
            
            if saved_path:
                st.toast("Analyzing Audio...")
                audio_res = analyze_audio_file(saved_path)
                st.session_state.results['audio'] = audio_res
                st.session_state.workflow_state = 'network'
                st.rerun()
            else:
                st.warning("No audio recorded. Did you speak?")
        else:
             st.warning("Please start the recording first.")

# 4. Network Check
elif st.session_state.workflow_state == 'network':
    st.header("Step 3: Network Check")
    st.info("Checking connection speed...")
    
    with st.spinner("Testing Download & Upload speeds..."):
        network_res = check_network_quality()
        st.session_state.results['network'] = network_res
        st.session_state.workflow_state = 'complete'
        st.rerun()

# 5. Results / Dashboard
elif st.session_state.workflow_state == 'complete':
    res = st.session_state.results
    
    # Analyze
    v_res = res.get('video', {})
    a_res = res.get('audio', {})
    n_res = res.get('network', {})
    
    v_rating, v_recs = analyze_video_results(v_res)
    a_rating, a_recs = analyze_audio_results(a_res)
    n_rating, n_recs = analyze_network_results(n_res)
    
    # Dashboard UI
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Video")
        if v_recs:
             for rec in v_recs: st.warning(rec, icon="⚠️")
        else:
             st.success("Video looks good!", icon="✅")
        st.metric("Rating", v_rating)
        st.divider()
        
        if "last_frame" in v_res:
             st.image(v_res['last_frame'], caption="Captured Frame")
             
        b_val = v_res.get('avg_brightness', 0)
        s_val = v_res.get('avg_sharpness', 0)
        st.write(f"**Brightness:** {get_star_rating(b_val, 40, 130)} ({b_val:.1f})")
        st.write(f"**Sharpness:** {get_star_rating(s_val, 50, 300)} ({s_val:.1f})")
        
        if v_res.get('face_detected'):
             h_val = v_res.get('avg_headroom', 0)
             st.write(f"**Headroom:** {get_star_rating(100 - abs(h_val - 15)*3, 0, 100)} ({h_val:.1f}%)")
        else:
             st.warning("No face detected.")

    with col2:
        st.subheader("Audio")
        if a_recs:
             for rec in a_recs: st.warning(rec, icon="⚠️")
        else:
             st.success("Audio sounds clear!", icon="✅")
        st.metric("Rating", a_rating)
        st.divider()
        
        vol_val = a_res.get('decibels', -100)
        snr_val = a_res.get('snr_db', 0)
        st.write(f"**Volume:** {get_star_rating(vol_val, -70, -35)} ({vol_val:.1f} dB)")
        st.write(f"**SNR:** {get_star_rating(snr_val, 10, 50)} ({snr_val:.1f} dB)")
        
        if "audio_path" in a_res:
             st.audio(a_res['audio_path'])

    with col3:
        st.subheader("Network")
        if n_recs:
             for rec in n_recs: st.warning(rec, icon="⚠️")
        else:
             st.success("Network stable!", icon="✅")
        st.metric("Rating", n_rating)
        st.divider()
        
        d_val = n_res.get('download_mbps', 0)
        u_val = n_res.get('upload_mbps', 0)
        p_val = n_res.get('ping_ms', 999)
        st.write(f"**Download:** {d_val:.1f} Mbps")
        st.write(f"**Upload:** {u_val:.1f} Mbps")
        st.write(f"**Ping:** {p_val:.0f} ms")
        
    st.divider()
    if st.button("Run Again", type="primary"):
        st.session_state.workflow_state = 'idle'
        st.rerun()
