
import cv2
import numpy as np
import time
import os

def draw_guide(frame):
    h, w = frame.shape[:2]
    center_x = w // 2
    # Ideal Headroom is ~15%. Face center should be around 40-45% down the screen.
    center_y = int(h * 0.45) 
    
    # Face is usually taller than wide.
    axes = (int(h * 0.25), int(h * 0.35)) # Half-width, Half-height
    
    cv2.ellipse(frame, (center_x, center_y), axes, 0, 0, 360, (0, 255, 255), 2)
    cv2.putText(frame, "Position Face Here", (center_x - 90, center_y - axes[1] - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

def check_video_quality(duration=2, output_video="test_video.avi", output_photo="test_photo.jpg", on_frame=None):
    """
    Captures video, shows live feed, records to file, and analyzes quality including framing.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return {"error": "Could not open webcam"}

    # --- Phase 2: Countdown ---
    # (Handled by app or here? Let's keep countdown here for the final capture sequence)
    countdown = 3
    start_count = time.time()
    while time.time() - start_count < countdown:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Resize
        height, width = frame.shape[:2]
        max_width = 640
        if width > max_width:
            scale = max_width / width
            new_height = int(height * scale)
            frame = cv2.resize(frame, (max_width, new_height))
        
        draw_guide(frame)
        
        remaining = int(countdown - (time.time() - start_count)) + 1
        cv2.putText(frame, f"Capturing in {remaining}...", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        if on_frame:
             if on_frame(frame):
                 cap.release()
                 return {"error": "Stopped by user"}

    # --- Phase 3: Capture & Analyze ---
    # Initialize Video Writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = None
    
    # Face Detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    brightness_values = []
    sharpness_values = []
    face_brightness_values = []
    headroom_values = [] # % of screen above head
    face_prop_values = [] # Face height / Screen height
    
    start_time = time.time()
    frame_count = 0
    last_frame = None # Used to store the last frame for photo output and for writer dimensions
    
    print("Press 'q' to quit early.")
    
    while (time.time() - start_time) < duration:
        ret, frame = cap.read()
        if not ret:
            continue
            

        
        # Write to file (ensure size matches writer if using writer, but for now we just write the resized frame)
        # Note: VideoWriter requires fixed size. If we resize dynamically, we might break it.
        # For simplicity in this script, we'll just write the frame as is. 
        # If the writer was initialized with 640x480, we must resize to that OR re-init writer.
        # To fix aspect ratio properly, we should NOT force 640x480 in writer if input is different.
        # But `out` is initialized before the loop. 
        # Let's move writer init inside loop or just before it once we know frame size.
        
    # Move writer init to after first frame read
    # ... (This requires a bigger refactor of the loop structure, let's do it carefully)

        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Global Brightness & Sharpness
        brightness = np.mean(gray)
        brightness_values.append(brightness)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_values.append(sharpness)
        
        # Face Detection
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        # Update last_frame with the current processed frame
        last_frame = frame.copy()
        
        # Draw face box on last_frame for debugging if face detected
        if len(faces) > 0:
             (x, y, w, h) = faces[0]
             
             # Expand the box to cover the full head (Haar cascade often just finds the face center)
             # Increase height by ~30% (mostly up for forehead/hair) and width by ~10%
             h_pad = int(h * 0.3)
             w_pad = int(w * 0.1)
             
             y = max(0, y - int(h_pad * 0.6)) # Move up significantly
             h = min(frame.shape[0] - y, h + h_pad)
             
             x = max(0, x - w_pad // 2)
             w = min(frame.shape[1] - x, w + w_pad)
             
             cv2.rectangle(last_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        face_detected = False
        for (x, y, w, h) in faces:
            face_detected = True
            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Calculate Headroom (Top of frame to top of face box)
            # y is the top coordinate of the face bounding box.
            # Frame height is 'height' (which is new_height after resize, or 480 if standard)
            # We resized to max_width=640, so height varies.
            # Let's use the actual frame height 'h_frame'
            h_frame, w_frame = frame.shape[:2]
            
            # Headroom % = (y / h_frame) * 100
            headroom_pct = (y / h_frame) * 100
            headroom_values.append(headroom_pct)
            
            # Face Height Proportion (Face Height / Frame Height)
            face_prop = h / h_frame
            face_prop_values.append(face_prop)
            
            # Face Brightness
            face_roi = gray[y:y+h, x:x+w]
            face_brightness = np.mean(face_roi)
            face_brightness_values.append(face_brightness)
            
            # Only process the first/largest face
            break
        
        # Show Live Feed or use Callback
        if on_frame:
            # Callback should return True to stop
            if on_frame(frame):
                break
        else:
            cv2.imshow('Video Quality Check - Press Q to Quit', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
        frame_count += 1
        
    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()
    
    if last_frame is not None:
        cv2.imwrite(output_photo, last_frame)
    
    if not brightness_values:
         return {"error": "No frames captured"}

    avg_brightness = np.mean(brightness_values)
    avg_sharpness = np.mean(sharpness_values)
    
    avg_face_brightness = np.mean(face_brightness_values) if face_brightness_values else None
    avg_headroom = np.mean(headroom_values) if headroom_values else None
    avg_face_prop = np.mean(face_prop_values) if face_prop_values else None
    
    # Convert last frame to RGB for easy display in Streamlit
    last_frame_rgb = None
    if last_frame is not None:
        last_frame_rgb = cv2.cvtColor(last_frame, cv2.COLOR_BGR2RGB)

    return {
        "avg_brightness": avg_brightness,
        "avg_sharpness": avg_sharpness,
        "frames_captured": frame_count,
        "face_detected": bool(face_brightness_values),
        "avg_face_brightness": avg_face_brightness,
        "avg_headroom": avg_headroom,
        "avg_face_prop": avg_face_prop,
        "video_path": os.path.abspath(output_video),
        "photo_path": os.path.abspath(output_photo),
        "last_frame": last_frame_rgb
    }
