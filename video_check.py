
import cv2
import numpy as np
import av
import threading

class VideoProcessor:
    def __init__(self):
        self.frame_lock = threading.Lock()
        self.brightness_values = []
        self.sharpness_values = []
        self.face_brightness_values = []
        self.headroom_values = []
        self.face_prop_values = []
        self.face_detected = False
        self.frame_count = 0
        self.last_frame = None
        
        # Load Haar Cascade
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # Resize for consistent analysis (optional, but good for performance)
        height, width = img.shape[:2]
        max_width = 640
        if width > max_width:
            scale = max_width / width
            new_height = int(height * scale)
            img = cv2.resize(img, (max_width, new_height))
            
        # Analysis
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Global Metrics
        brightness = np.mean(gray)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        with self.frame_lock:
            self.brightness_values.append(brightness)
            self.sharpness_values.append(sharpness)
            self.frame_count += 1
            self.last_frame = img.copy()
        
        # 2. Face Detection
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        detected_this_frame = False
        for (x, y, w, h) in faces:
            detected_this_frame = True
            
            # Draw Face Box
            cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Headroom & Face Prop Analysis
            h_frame, w_frame = img.shape[:2]
            headroom_pct = (y / h_frame) * 100
            face_prop = h / h_frame
            
            # Face Brightness
            face_roi = gray[y:y+h, x:x+w]
            face_brightness = np.mean(face_roi)
            
            with self.frame_lock:
                self.headroom_values.append(headroom_pct)
                self.face_prop_values.append(face_prop)
                self.face_brightness_values.append(face_brightness)
                self.face_detected = True
                
            break # Process only largest face
            
        # Draw Guide (Ellipse)
        h, w = img.shape[:2]
        center_x = w // 2
        center_y = int(h * 0.45)
        axes = (int(h * 0.25), int(h * 0.35))
        cv2.ellipse(img, (center_x, center_y), axes, 0, 0, 360, (0, 255, 255), 2)
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

    def get_stats(self):
        with self.frame_lock:
            if not self.brightness_values:
                return None
                
            avg_brightness = np.mean(self.brightness_values)
            avg_sharpness = np.mean(self.sharpness_values)
            avg_face_brightness = np.mean(self.face_brightness_values) if self.face_brightness_values else None
            avg_headroom = np.mean(self.headroom_values) if self.headroom_values else None
            avg_face_prop = np.mean(self.face_prop_values) if self.face_prop_values else None
            
            # Convert last frame to RGB for display
            last_frame_rgb = None
            if self.last_frame is not None:
                last_frame_rgb = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)

            return {
                "avg_brightness": avg_brightness,
                "avg_sharpness": avg_sharpness,
                "frames_captured": self.frame_count,
                "face_detected": self.face_detected,
                "avg_face_brightness": avg_face_brightness,
                "avg_headroom": avg_headroom,
                "avg_face_prop": avg_face_prop,
                "last_frame": last_frame_rgb
            }
