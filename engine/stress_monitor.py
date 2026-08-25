import os
import cv2
import time
import json
import sqlite3
import threading
import numpy as np
from collections import deque
from PIL import Image
from google import genai
from google.genai import types

base_dir = os.path.dirname(os.path.abspath(__file__))
cascade_path = os.path.join(base_dir, 'auth', 'haarcascade_frontalface_default.xml')
db_path = os.path.join(os.path.dirname(base_dir), 'jarvis.db')

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyBnqh7CyKty76H1eqBXmOwpkqhRuxX3IDU')


class StressMonitorEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StressMonitorEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.is_running = False
        self.monitor_thread = None
        self.cap = None
        self.frame_lock = threading.Lock()
        self.latest_annotated_frame = None

        # ── Real-time biometric state ──
        self.current_score = 15
        self.current_state = "Calm & Relaxed"
        self.current_advice = "Your stress levels are normal. Keep up the good work!"
        self.face_detected = False
        self.estimated_hr = 0  # BPM
        self.posture_status = "Good"
        self.fatigue_level = "Normal"

        # ── Timing ──
        self.last_ai_check_time = 0
        self.high_stress_counter = 0
        self.last_intervention_time = 0

        # ── rPPG signal buffers (rolling 10-second window at ~30 FPS → 300 samples) ──
        self.rppg_buffer_size = 300
        self.green_signal = deque(maxlen=self.rppg_buffer_size)
        self.rppg_timestamps = deque(maxlen=self.rppg_buffer_size)

        # ── Posture tracking ──
        self.baseline_face_y = None
        self.baseline_face_area = None
        self.face_y_history = deque(maxlen=60)
        self.face_area_history = deque(maxlen=60)

        # ── Micro-tension / fatigue ──
        self.brow_variance_history = deque(maxlen=90)

        # ── Smoothed real-time score ──
        self.smoothed_score = 15.0

        # ── Score history for trends (last 120 readings ~ 1 min at 500ms updates) ──
        self.score_history = deque(maxlen=120)

        # ── OpenCV cascade ──
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.init_db()

    # ─────────────────────── Database ───────────────────────

    def init_db(self):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS stress_logs
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              stress_score INTEGER NOT NULL,
                              state TEXT NOT NULL,
                              advice TEXT NOT NULL,
                              timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing stress_logs table: {e}")

    def log_stress(self, score, state, advice):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO stress_logs (stress_score, state, advice) VALUES (?, ?, ?)",
                           (score, state, advice))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging stress record: {e}")

    # ─────────────────────── rPPG Pulse Estimation ───────────────────────

    def extract_rppg_signal(self, face_roi_bgr):
        """Extract green-channel chrominance mean from forehead region for rPPG."""
        try:
            h, w = face_roi_bgr.shape[:2]
            # Forehead region: top 30% of face, central 60%
            forehead = face_roi_bgr[int(h * 0.05):int(h * 0.30), int(w * 0.2):int(w * 0.8)]
            if forehead.size == 0:
                return
            green_mean = np.mean(forehead[:, :, 1])  # Green channel
            self.green_signal.append(green_mean)
            self.rppg_timestamps.append(time.time())
        except Exception:
            pass

    def estimate_heart_rate(self):
        """Estimate heart rate from green-channel temporal signal using FFT."""
        try:
            if len(self.green_signal) < 90:  # Need at least 3 seconds of data
                return 0
            signal = np.array(self.green_signal)
            timestamps = np.array(self.rppg_timestamps)

            # Compute sampling rate
            dt = np.diff(timestamps)
            if len(dt) == 0 or np.mean(dt) == 0:
                return 0
            fs = 1.0 / np.mean(dt)

            # Detrend: subtract rolling mean
            kernel_size = min(int(fs * 1.5), len(signal) // 2)
            if kernel_size < 3:
                kernel_size = 3
            if kernel_size % 2 == 0:
                kernel_size += 1
            kernel = np.ones(kernel_size) / kernel_size
            trend = np.convolve(signal, kernel, mode='same')
            detrended = signal - trend

            # Apply Hanning window
            window = np.hanning(len(detrended))
            windowed = detrended * window

            # FFT
            n = len(windowed)
            fft_vals = np.abs(np.fft.rfft(windowed))
            freqs = np.fft.rfftfreq(n, d=1.0 / fs)

            # Bandpass: 0.75 Hz – 3.0 Hz (45–180 BPM)
            valid_mask = (freqs >= 0.75) & (freqs <= 3.0)
            if not np.any(valid_mask):
                return 0
            valid_fft = fft_vals[valid_mask]
            valid_freqs = freqs[valid_mask]

            # Peak frequency
            peak_idx = np.argmax(valid_fft)
            peak_freq = valid_freqs[peak_idx]
            bpm = int(peak_freq * 60)

            return max(45, min(180, bpm))
        except Exception:
            return 0

    # ─────────────────────── Posture Analysis ───────────────────────

    def analyze_posture(self, face_y, face_area):
        """Detect slouching by comparing face position and size to baseline."""
        self.face_y_history.append(face_y)
        self.face_area_history.append(face_area)

        if self.baseline_face_y is None and len(self.face_y_history) >= 30:
            self.baseline_face_y = np.median(list(self.face_y_history))
            self.baseline_face_area = np.median(list(self.face_area_history))

        if self.baseline_face_y is not None:
            y_shift = face_y - self.baseline_face_y
            area_ratio = face_area / max(self.baseline_face_area, 1)

            # Slouching: face drops down significantly or gets much larger (closer to screen)
            if y_shift > 40 or area_ratio > 1.35:
                self.posture_status = "Slouching"
                return 0.7  # stress contribution
            elif y_shift > 20 or area_ratio > 1.15:
                self.posture_status = "Mild Slouch"
                return 0.4
            else:
                self.posture_status = "Good"
                return 0.0
        self.posture_status = "Calibrating"
        return 0.0

    # ─────────────────────── Brow/Eye Micro-Tension ───────────────────────

    def analyze_brow_tension(self, gray_face):
        """Compute high-frequency texture variance in upper face (brow/eye area)."""
        try:
            h, w = gray_face.shape[:2]
            brow_region = gray_face[int(h * 0.1):int(h * 0.45), int(w * 0.15):int(w * 0.85)]
            if brow_region.size == 0:
                return 0.0
            # Laplacian gives high-frequency detail (wrinkle/tension indicator)
            laplacian = cv2.Laplacian(brow_region, cv2.CV_64F)
            variance = laplacian.var()
            self.brow_variance_history.append(variance)

            if len(self.brow_variance_history) >= 30:
                median_var = np.median(list(self.brow_variance_history))
                if variance > median_var * 1.5:
                    self.fatigue_level = "High"
                    return 0.6
                elif variance > median_var * 1.2:
                    self.fatigue_level = "Moderate"
                    return 0.3
            self.fatigue_level = "Normal"
            return 0.0
        except Exception:
            return 0.0

    # ─────────────────────── Real-Time Stress Synthesis ───────────────────────

    def compute_realtime_score(self, face_detected, posture_stress, tension_stress, hr):
        """Blend biometric signals into a single smoothed stress score."""
        if not face_detected:
            # Decay gently when no face
            target = max(self.smoothed_score - 0.5, 15)
        else:
            # Base from resting level
            base = 15

            # Heart rate contribution (resting ~60-80 is normal)
            hr_stress = 0.0
            if hr > 0:
                if hr > 100:
                    hr_stress = min((hr - 100) / 80.0, 1.0) * 30
                elif hr < 55:
                    hr_stress = 5  # Very low HR can indicate fatigue

            # Posture contribution (0-0.7 → 0-20 points)
            posture_contrib = posture_stress * 20

            # Tension/fatigue contribution (0-0.6 → 0-20 points)
            tension_contrib = tension_stress * 25

            # Movement instability (jitter from face position variance)
            jitter = 0
            if len(self.face_y_history) >= 10:
                recent_y = list(self.face_y_history)[-10:]
                jitter = min(np.std(recent_y) / 10.0, 1.0) * 10

            target = base + hr_stress + posture_contrib + tension_contrib + jitter
            target = max(0, min(100, target))

        # Exponential moving average for smooth transitions
        alpha = 0.15
        self.smoothed_score = self.smoothed_score * (1 - alpha) + target * alpha
        self.current_score = int(round(self.smoothed_score))

        # Classify state
        if self.current_score >= 75:
            self.current_state = "High Stress"
        elif self.current_score >= 55:
            self.current_state = "Moderate Stress"
        elif self.current_score >= 35:
            self.current_state = "Mild Tension"
        elif self.current_score >= 20:
            self.current_state = "Focused"
        else:
            self.current_state = "Calm & Relaxed"

        self.score_history.append(self.current_score)

    # ─────────────────────── HUD Overlay Rendering ───────────────────────

    def draw_hud_overlay(self, frame, faces):
        """Draw futuristic Jarvis-style HUD targeting reticles and telemetry on frame."""
        h, w = frame.shape[:2]
        overlay = frame.copy()

        # Semi-transparent dark border strips
        cv2.rectangle(overlay, (0, 0), (w, 32), (10, 15, 25), -1)
        cv2.rectangle(overlay, (0, h - 28), (w, h), (10, 15, 25), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Top-left: JARVIS OS tag
        cv2.putText(frame, "JARVIS STRESS MONITOR", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)

        # Top-right: timestamp
        ts = time.strftime("%H:%M:%S")
        cv2.putText(frame, ts, (w - 90, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)

        # Bottom telemetry bar
        score_color = (0, 230, 118) if self.current_score < 35 else (0, 229, 255) if self.current_score < 60 else (0, 145, 255) if self.current_score < 80 else (0, 23, 255)
        cv2.putText(frame, f"STRESS: {self.current_score}%", (10, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, score_color, 1, cv2.LINE_AA)

        hr_text = f"PULSE: {self.estimated_hr} BPM" if self.estimated_hr > 0 else "PULSE: ---"
        cv2.putText(frame, hr_text, (180, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"POSTURE: {self.posture_status.upper()}", (380, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)

        # Face targeting brackets
        for (x, y, fw, fh) in faces:
            bracket_len = int(min(fw, fh) * 0.25)
            color = (0, 255, 200)  # Neon cyan-green

            # Top-left bracket
            cv2.line(frame, (x, y), (x + bracket_len, y), color, 2)
            cv2.line(frame, (x, y), (x, y + bracket_len), color, 2)
            # Top-right bracket
            cv2.line(frame, (x + fw, y), (x + fw - bracket_len, y), color, 2)
            cv2.line(frame, (x + fw, y), (x + fw, y + bracket_len), color, 2)
            # Bottom-left bracket
            cv2.line(frame, (x, y + fh), (x + bracket_len, y + fh), color, 2)
            cv2.line(frame, (x, y + fh), (x, y + fh - bracket_len), color, 2)
            # Bottom-right bracket
            cv2.line(frame, (x + fw, y + fh), (x + fw - bracket_len, y + fh), color, 2)
            cv2.line(frame, (x + fw, y + fh), (x + fw, y + fh - bracket_len), color, 2)

            # Crosshair center dot
            cx, cy = x + fw // 2, y + fh // 2
            cv2.circle(frame, (cx, cy), 3, color, -1)

            # rPPG forehead ROI indicator
            forehead_y1 = y + int(fh * 0.05)
            forehead_y2 = y + int(fh * 0.30)
            forehead_x1 = x + int(fw * 0.2)
            forehead_x2 = x + int(fw * 0.8)
            cv2.rectangle(frame, (forehead_x1, forehead_y1), (forehead_x2, forehead_y2), (0, 180, 255), 1)
            cv2.putText(frame, "rPPG", (forehead_x1, forehead_y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 180, 255), 1, cv2.LINE_AA)

        # No face indicator
        if len(faces) == 0:
            cv2.putText(frame, "NO FACE DETECTED", (w // 2 - 110, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

        return frame

    # ─────────────────────── Gemini Deep Analysis ───────────────────────

    def analyze_face_frame(self, face_rgb_img):
        """Send face image crop to Gemini 2.5 Flash Vision for deep stress analysis."""
        try:
            client = genai.Client(api_key=GOOGLE_API_KEY)
            prompt = (
                "You are an AI wellness and stress monitoring assistant. "
                "Analyze this user's facial expression, eye fatigue, brow tension, and posture from this webcam frame. "
                "Output STRICTLY a JSON object with three keys:\n"
                "- 'stress_score': integer from 0 (completely relaxed) to 100 (extreme stress/fatigue)\n"
                "- 'state': short 2-4 word status (e.g. 'Calm & Relaxed', 'Focused', 'Mild Eye Strain', 'High Stress & Tension')\n"
                "- 'advice': 1 brief, encouraging actionable relief sentence.\n"
                "Example JSON: {\"stress_score\": 35, \"state\": \"Mild Eye Strain\", \"advice\": \"Take 20 seconds to look at a distant object to relax your eyes.\"}"
            )
            response = None
            for model_name in ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.5-flash-lite']:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[face_rgb_img, prompt]
                    )
                    if response and response.text:
                        break
                except Exception:
                    continue

            if not response or not response.text:
                return None

            raw_text = response.text.strip()

            # Clean markdown codeblocks if present
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            score = int(parsed.get('stress_score', 25))
            state = str(parsed.get('state', 'Normal'))
            advice = str(parsed.get('advice', 'Remember to stay hydrated and take brief breaks.'))
            return score, state, advice
        except Exception as e:
            print(f"AI Vision stress analysis fallback: {e}")
            return None

    # ─────────────────────── Main Monitor Loop ───────────────────────

    def _monitor_loop(self):
        print("Real-Time AI Camera Stress Monitor started (30 FPS).")
        try:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
        except Exception as e:
            print(f"Camera open error: {e}")
            self.cap = None

        while self.is_running:
            try:
                if self.cap is None or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    time.sleep(1)
                    if not self.cap.isOpened():
                        time.sleep(2)
                        continue

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.03)
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(80, 80))

                now = time.time()
                posture_stress = 0.0
                tension_stress = 0.0

                if len(faces) > 0:
                    self.face_detected = True
                    (x, y, w, h) = faces[0]
                    face_center_y = y + h // 2
                    face_area = w * h

                    # ── Real-time rPPG extraction ──
                    margin_y = int(0.1 * h)
                    margin_x = int(0.1 * w)
                    y1 = max(0, y - margin_y)
                    y2 = min(frame.shape[0], y + h + margin_y)
                    x1 = max(0, x - margin_x)
                    x2 = min(frame.shape[1], x + w + margin_x)
                    face_crop = frame[y1:y2, x1:x2]
                    self.extract_rppg_signal(face_crop)

                    # ── Estimate heart rate ──
                    hr = self.estimate_heart_rate()
                    if hr > 0:
                        self.estimated_hr = hr

                    # ── Posture analysis ──
                    posture_stress = self.analyze_posture(face_center_y, face_area)

                    # ── Brow/eye tension ──
                    gray_face = gray[max(0, y):min(gray.shape[0], y + h), max(0, x):min(gray.shape[1], x + w)]
                    tension_stress = self.analyze_brow_tension(gray_face)

                    # ── Periodic deep Gemini AI analysis (every 60 seconds) ──
                    if now - self.last_ai_check_time >= 60:
                        self.last_ai_check_time = now
                        face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(face_rgb)

                        # Run AI analysis in a separate thread to not block FPS
                        def _ai_analyze(img):
                            result = self.analyze_face_frame(img)
                            if result:
                                ai_score, ai_state, ai_advice = result
                                # Blend AI score into smoothed score
                                self.smoothed_score = self.smoothed_score * 0.6 + ai_score * 0.4
                                self.current_advice = ai_advice
                                self.log_stress(ai_score, ai_state, ai_advice)

                                if ai_score > 40:
                                    self.high_stress_counter += 1
                                else:
                                    self.high_stress_counter = 0

                                if self.high_stress_counter >= 1 and (now - self.last_intervention_time >= 90):
                                    self.last_intervention_time = time.time()
                                    self.trigger_proactive_intervention(ai_score, ai_advice)

                        threading.Thread(target=_ai_analyze, args=(pil_img,), daemon=True).start()

                else:
                    self.face_detected = False

                # ── Compute real-time stress score ──
                self.compute_realtime_score(self.face_detected, posture_stress, tension_stress, self.estimated_hr)

                # ── Auto-Intervention check when real-time stress exceeds 40% ──
                if self.current_score > 40 and (now - self.last_intervention_time >= 90):
                    self.last_intervention_time = now
                    def _auto_help():
                        self.trigger_proactive_intervention(self.current_score, self.current_advice)
                    threading.Thread(target=_auto_help, daemon=True).start()

                # ── Draw HUD overlay and store annotated frame ──
                annotated = self.draw_hud_overlay(frame, faces)
                with self.frame_lock:
                    self.latest_annotated_frame = annotated.copy()

                # ~30 FPS
                time.sleep(0.033)

            except Exception as e:
                print(f"Error in real-time stress monitor loop: {e}")
                time.sleep(1)

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        print("Real-Time AI Camera Stress Monitor stopped.")

    # ─────────────────────── Video Feed Generator ───────────────────────

    def generate_video_frames(self):
        """Generator yielding MJPEG frames for live video streaming."""
        while self.is_running:
            with self.frame_lock:
                frame = self.latest_annotated_frame
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.033)

    # ─────────────────────── Proactive Intervention ───────────────────────

    def trigger_proactive_intervention(self, score, advice):
        """Notify user via speech & UI about elevated stress (> 40%)."""
        try:
            from engine.command import speak
            msg = f"Sir, I notice your stress level is at {score} percent, which exceeds 40 percent threshold. {advice} Automatically launching Relief Center for your breathing exercise."
            print(f"[Proactive Relief Alert (>40%)]: {msg}")
            speak(msg)
            try:
                import eel
                eel.trigger_relief_intervention()()
            except Exception:
                pass
        except Exception as e:
            print(f"Failed to speak proactive intervention: {e}")

    # ─────────────────────── Start / Stop / Status ───────────────────────

    def start(self):
        if self.is_running:
            return True
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        return True

    def stop(self):
        self.is_running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        return True

    def get_status(self):
        return {
            "active": self.is_running,
            "score": self.current_score,
            "state": self.current_state,
            "advice": self.current_advice,
            "face_detected": self.face_detected,
            "heart_rate": self.estimated_hr,
            "posture": self.posture_status,
            "fatigue": self.fatigue_level,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


# Global Singleton Instance
stress_engine = StressMonitorEngine()
