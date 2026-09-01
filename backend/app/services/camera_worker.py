"""Camera worker - one instance per camera row in the DB.

This is a direct port of the old camrea_worker.py `CameraWorker(QThread)`.
The detection pipeline (face gatekeeper -> auth every 30 frames -> PPE YOLO
-> hand-wash + WHO-step tracking -> master_ready decision -> log_and_notify
on logout) is unchanged. What changed is only the plumbing:
  - QThread -> threading.Thread
  - pyqtSignal emits -> updates to self.latest_jpeg / self.latest_status,
    read by the FastAPI MJPEG/status endpoints.
  - `config.SINK_CAMERAS[name]` hardcoded source -> `camera.source` from DB,
    can be a webcam index or an RTSP/HTTP URL, added/changed at runtime.
"""
import sys
import time
import threading
import logging

import cv2

from app.ai.ai_models import AIModels, recognize_face_sync
from app.ai.hand_wash_detector import HandWashDetector
from app.services.data_logger import DataLogger, UserSessionManager
from app.services import settings_store as cfg


class ZeroLatencyGrabber:
    """Unchanged from the original - a dedicated thread that constantly
    clears the camera buffer for both USB indices and IP/RTSP URLs."""

    def __init__(self, src):
        #gemini
        if str(src).isdigit():
            self.src = int(src)
        else:
            self.src = src

        #gemini
        self.ret = False
        self.frame = None
        self.stopped = False
        self.lock = threading.Lock()
        self.last_frame_time = time.time()

    def start(self):
        threading.Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        # src is an int (webcam index) or a string (RTSP/HTTP URL).
        # Original app forced CAP_DSHOW on Windows to avoid a 1s OBS/virtual-cam
        # freeze - kept here, but only on Windows, so this also runs on Linux/Mac.
        if isinstance(self.src, int):
            if sys.platform.startswith("win"):
                stream = cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
            else:
                stream = cv2.VideoCapture(self.src)
        else:
            stream = cv2.VideoCapture(self.src)
            stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while not self.stopped:
            ret, frame = stream.read()
            with self.lock:
                self.ret = ret
                if ret:
                    self.frame = frame
                    self.last_frame_time = time.time()
        stream.release()

    def read(self):
        with self.lock:
            return self.ret, self.frame.copy() if self.ret else None

    def stop(self):
        self.stopped = True


class CameraStream:
    """Replaces CameraWorker(QThread). One per camera, started/stopped
    dynamically by camera_manager.py - never hardcoded."""

    def __init__(self, camera_id, camera_name, source):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.source = source
        self.running = False
        self.thread = None

        self.ai_models = None
        self.wash_detector = HandWashDetector()
        self.session_manager = UserSessionManager()
        self.data_logger = DataLogger()

        self.video_stream = None
        self.sink_y_start = None
        self.manual_roi = None  # normalized [x1,y1,x2,y2], settable live

        self.check_mask = True
        self.check_hat = True
        self.check_wash = True

        self.auth_check_counter = 0
        self.auth_message = "WAITING FOR FACE..."
        self.auth_color = "normal"

        self._frame_lock = threading.Lock()
        self.latest_jpeg = None
        self.latest_status = {
            "camera_id": camera_id,
            "camera_name": camera_name,
            "user": "EMPTY",
            "is_auth": False,
            "auth_msg": self.auth_message,
            "auth_color": self.auth_color,
            "mask": False,
            "hat": False,
            "check_mask": True,
            "check_hat": True,
            "check_wash": True,
            "wash_time": 0,
            "wash_status": "STANDBY",
            "master_ready": False,
            "connected": False,
        }

    # ---- lifecycle -------------------------------------------------
    def start(self):
        if self.running:
            return
        self.ai_models = AIModels()
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.video_stream:
            self.video_stream.stop()
        if self.thread:
            self.thread.join(timeout=3)
        if self.ai_models:
            self.ai_models.cleanup()

    def update_toggles(self, mask, hat, wash):
        self.check_mask = mask
        self.check_hat = hat
        self.check_wash = wash

    def set_manual_roi(self, roi):
        self.manual_roi = roi
        self.sink_y_start = None

    def trigger_calibration(self):
        self.sink_y_start = None
        self.manual_roi = None

    # ---- frame/status accessors used by the API ---------------------
    def get_jpeg(self):
        with self._frame_lock:
            return self.latest_jpeg

    def get_status(self):
        with self._frame_lock:
            return dict(self.latest_status)

    # ---- main loop (ported from CameraWorker.run) --------------------
    def _run(self):
        logging.info(f"[INFO] Connecting to camera '{self.camera_name}' ({self.source})...")
        self.video_stream = ZeroLatencyGrabber(self.source).start()

        while self.running:
            now = time.time()
            if now - self.video_stream.last_frame_time > 5.0:
                logging.warning(f"[WATCHDOG] '{self.camera_name}' stream hung, restarting...")
                self.video_stream.stop()
                self.video_stream = ZeroLatencyGrabber(self.source).start()
                self.video_stream.last_frame_time = time.time()
                time.sleep(1)
                continue

            ret, frame = self.video_stream.read()
            if not ret or frame is None:
                self._set_status_field("connected", False)
                time.sleep(0.01)
                continue
            self._set_status_field("connected", True)

            frame_h, frame_w = frame.shape[:2]
            clean_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            hand_results = self.ai_models.detect_hands(clean_rgb)
            has_any_face = self.ai_models.detect_face(clean_rgb)

            if self.session_manager.is_authenticated() and (has_any_face or hand_results['detected']):
                self.session_manager.update_presence()

            if has_any_face:
                self.auth_check_counter += 1
                if self.auth_check_counter % 30 == 0:
                    if not self.session_manager.is_authenticating and self.session_manager.can_attempt_auth():
                        self.session_manager.is_authenticating = True
                        self.auth_message = "SCANNING FACE..."
                        self.auth_color = "warning"
                        auth_result = recognize_face_sync(frame.copy())
                        self.handle_auth_result(auth_result)
            else:
                self.auth_check_counter = 0
                if self.session_manager.check_presence_timeout():
                    self.logout_user()
                    self.auth_message = "WAITING FOR FACE..."
                    self.auth_color = "normal"

            # Scrub-zone: use a saved manual ROI's top edge if the camera
            # was calibrated from the UI, otherwise fall back to the same
            # 50/50 split the original app used. Never hardcoded to one
            # camera - each camera's zone is computed from ITS OWN settings.
            if self.manual_roi:
                self.sink_y_start = int(self.manual_roi[1] * frame_h)
            else:
                self.sink_y_start = int(frame_h * 0.5)

            cv2.line(frame, (0, self.sink_y_start), (frame_w, self.sink_y_start), (0, 0, 255), 2)
            cv2.putText(frame, "SCRUB ZONE", (10, self.sink_y_start - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            has_mask, has_hat = False, False

            if self.session_manager.is_authenticated():
                if self.check_mask or self.check_hat:
                    frame, has_mask, has_hat = self.ai_models.detect_ppe(frame)

                if self.check_wash and hand_results['detected']:
                    frame = self.ai_models.draw_hand_landmarks(frame, hand_results['hand_results'])
                    wash_info = self.wash_detector.detect_washing(
                        hand_results, frame_w, frame_h, self.sink_y_start, self.ai_models
                    )

                    if wash_info['actively_washing']:
                        current_who_step = self.ai_models.predict_who_step(hand_results['hand_results'])
                        is_valid_who_step = (1 <= current_who_step <= 6)
                        self.wash_detector.update_wash_time(True)

                        if is_valid_who_step:
                            self.wash_detector.completed_steps.add(current_who_step)

                        step_labels = {
                            0: "PAUSED: Incorrect Gesture / Transition",
                            1: "Step 1: Palm to Palm",
                            2: "Step 2: Right over Left Dorsum",
                            3: "Step 3: Palm to Palm Interlaced",
                            4: "Step 4: Backs of Fingers",
                            5: "Step 5: Thumb Rotation",
                            6: "Step 6: Fingertips"
                        }
                        label_text = step_labels.get(current_who_step, "Detecting...")
                        bg_color = (27, 67, 50) if is_valid_who_step else (0, 0, 150)
                        border_color = (0, 255, 0) if is_valid_who_step else (0, 165, 255)
                        cv2.rectangle(frame, (20, 30), (460, 80), bg_color, -1)
                        cv2.rectangle(frame, (20, 30), (460, 80), border_color, 2)
                        cv2.putText(frame, label_text, (35, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2)
                    else:
                        self.wash_detector.update_wash_time(False)
                        self.ai_models.clear_buffer()

                    frame = self.wash_detector.draw_bubble_zone(frame)
                else:
                    self.wash_detector.update_wash_time(False)
                    self.ai_models.clear_buffer()
            else:
                self.wash_detector.reset_state()
                self.ai_models.clear_buffer()

            master_ready = False
            if self.session_manager.is_authenticated():
                master_ready = True
                if self.check_mask and not has_mask:
                    master_ready = False
                if self.check_hat and not has_hat:
                    master_ready = False
                if self.check_wash and self.wash_detector.current_wash_time < cfg.get("min_wash_time"):
                    master_ready = False

            status = {
                "camera_id": self.camera_id,
                "camera_name": self.camera_name,
                "user": self.session_manager.current_user if self.session_manager.current_user else "EMPTY",
                "is_auth": self.session_manager.is_authenticated(),
                "auth_msg": self.auth_message,
                "auth_color": self.auth_color,
                "mask": has_mask,
                "hat": has_hat,
                "check_mask": self.check_mask,
                "check_hat": self.check_hat,
                "check_wash": self.check_wash,
                "wash_time": self.wash_detector.current_wash_time,
                "wash_status": self.wash_detector.get_wash_status(hand_results.get('count', 0)) if hand_results else "STANDBY",
                "master_ready": master_ready,
                "connected": True,
            }

            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            with self._frame_lock:
                if ok:
                    self.latest_jpeg = buf.tobytes()
                self.latest_status = status

        if self.video_stream:
            self.video_stream.stop()

    def _set_status_field(self, key, value):
        with self._frame_lock:
            self.latest_status[key] = value

    # ---- auth / logout (ported unchanged) -----------------------------
    def handle_auth_result(self, result):
        self.session_manager.is_authenticating = False
        self.session_manager.set_auth_attempt()
        clean_result = result.replace("_", " ")

        if result in ("NO_FACE", "UNKNOWN"):
            if not self.session_manager.is_authenticated():
                self.auth_message = "UNKNOWN USER"
                self.auth_color = "error"
            return

        if not self.session_manager.is_authenticated():
            self.session_manager.set_user(clean_result)
            self.wash_detector.reset_state()
            self.auth_message = f"{clean_result} LOGGED IN"
            self.auth_color = "success"
        elif self.session_manager.current_user != clean_result:
            logging.info(f"[{self.camera_name} SWAP] {self.session_manager.current_user} left, {clean_result} in.")
            self.logout_user()
            self.session_manager.set_user(clean_result)
            self.wash_detector.reset_state()
            self.auth_message = f"SWAPPED TO {clean_result}"
            self.auth_color = "success"
        else:
            self.session_manager.update_presence()

    def logout_user(self):
        if self.session_manager.is_authenticated():
            wash_duration = int(self.wash_detector.current_wash_time)
            wash_status = "YES" if self.wash_detector.current_wash_time >= cfg.get("min_wash_time") else "NO"
            mask_status = "YES" if (self.session_manager.last_person_seen_time - self.wash_detector.last_mask_seen_time) <= 3.0 else "NO"
            hat_status = "YES" if (self.session_manager.last_person_seen_time - self.wash_detector.last_hat_seen_time) <= 3.0 else "NO"
            all_steps = "YES" if len(self.wash_detector.completed_steps) >= 4 else "NO"

            self.data_logger.log_and_notify(
                self.camera_id, self.camera_name,
                self.session_manager.current_user, self.session_manager.login_time,
                wash_status, mask_status, hat_status, all_steps, wash_duration
            )

        self.session_manager.clear_user()
        self.wash_detector.reset_state()
        self.wash_detector.current_wash_time = 0.0
        self.ai_models.clear_buffer()
