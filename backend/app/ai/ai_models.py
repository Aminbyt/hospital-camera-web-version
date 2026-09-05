"""AI Detection Module - YOLO, InsightFace, MediaPipe, WHO Handwashing LSTM.

Ported from the original desktop `ai_models.py`. All detection logic,
thresholds-usage, and algorithms are UNCHANGED - the only differences are:
  - No PyQt5 QThread wrapper (the web backend calls recognize_face_sync
    directly from inside its own worker thread, so the wrapper was dead
    weight).
  - Thresholds/paths come from settings_store / app.config instead of a
    hardcoded config.py module.
"""
import os
import pickle
import threading
import math
from collections import Counter, deque

import cv2
import numpy as np
import joblib  # kept for parity with original (RF fallback model support)
import pandas as pd
from ultralytics import YOLO
import mediapipe as mp

from app.config import env, REG_PATH
from app.services import settings_store as cfg

GLOBAL_INSIGHT_APP = None
GLOBAL_DB_EMBEDDINGS = {}
FACE_LOCK = threading.RLock()


def _face_cache_path():
    return os.path.join(env.DATA_ROOT, "face_cache.pkl")


def _largest_face(faces):
    """Return the largest detected face. This keeps registration and live
    recognition focused on the person closest to the sink camera instead of
    relying on InsightFace detection ordering.
    """
    if not faces:
        return None

    def area(face):
        try:
            x1, y1, x2, y2 = face.bbox
            return max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))
        except Exception:
            return 0.0

    return max(faces, key=area)




def _safe_face_embedding(face):
    """Return a finite L2-normalized InsightFace embedding or None.

    Prefer InsightFace's `normed_embedding` because that is what the original
    project used successfully. If it is unavailable or invalid, fall back to
    the raw `embedding` and normalize it ourselves.
    """
    if face is None:
        return None

    # Try both representations independently. IMPORTANT: an existing but
    # invalid raw embedding must not prevent us from trying normed_embedding.
    candidates = [
        ("normed_embedding", getattr(face, "normed_embedding", None)),
        ("embedding", getattr(face, "embedding", None)),
    ]

    for source_name, raw in candidates:
        if raw is None:
            continue
        try:
            vec = np.asarray(raw, dtype=np.float32).reshape(-1)
        except Exception:
            continue
        if vec.size == 0 or not np.all(np.isfinite(vec)):
            continue

        norm = float(np.linalg.norm(vec))
        if not np.isfinite(norm) or norm <= 1e-12:
            continue

        return vec / norm

    return None


def _embed_person_folder(person_dir, person_name):
    """Runs InsightFace over every photo in a person's folder and returns
    the list of embeddings. Used both for the first-time full scan and for
    incrementally picking up people added directly on disk."""
    embeddings = []
    for img_name in os.listdir(person_dir):
        if img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            img_path = os.path.join(person_dir, img_name)
            db_img = cv2.imread(img_path)
            if db_img is not None:
                faces = GLOBAL_INSIGHT_APP.get(db_img)
                face = _largest_face(faces)
                if face is not None:
                    embedding = _safe_face_embedding(face)
                    if embedding is not None:
                        embeddings.append(embedding)
                    else:
                        print(f"  [WARNING] Invalid face embedding in {img_name}")
                else:
                    print(f"  [WARNING] No face detected in {img_name}")
    return embeddings


def initialize_face_engine(db_path):
    """Initializes InsightFace and loads staff photo embeddings ONCE at system boot.

    IMPORTANT: after loading the cache (or on every call, really), this also
    reconciles GLOBAL_DB_EMBEDDINGS against what's actually in db_path. Staff
    folders added directly on disk (copied in manually, not through
    /api/registration/capture) used to be silently invisible to recognition
    until reset_face_cache() was called by hand - everyone would just keep
    matching whoever was in the cache first. Now any folder present on disk
    but missing from the in-memory/cached embeddings gets picked up
    automatically.
    """
    global GLOBAL_INSIGHT_APP, GLOBAL_DB_EMBEDDINGS

    with FACE_LOCK:
        try:
            if GLOBAL_INSIGHT_APP is None:
                print("[INFO] Initializing InsightFace Engine...")
                from insightface.app import FaceAnalysis
                GLOBAL_INSIGHT_APP = FaceAnalysis(name='antelopev2', providers=['CPUExecutionProvider'])
                GLOBAL_INSIGHT_APP.prepare(ctx_id=0, det_thresh=0.35, det_size=(640, 640))
                print("[INFO] InsightFace Engine initialized successfully!")

            cache_path = _face_cache_path()

            if not GLOBAL_DB_EMBEDDINGS and os.path.exists(cache_path):
                print("[INFO] Loading face embeddings from cache...")
                with open(cache_path, 'rb') as f:
                    GLOBAL_DB_EMBEDDINGS = pickle.load(f)
                print(f"[INFO] Loaded {len(GLOBAL_DB_EMBEDDINGS)} staff members from cache.")

            if not os.path.exists(db_path):
                os.makedirs(db_path, exist_ok=True)
                return

            # --- Reconcile: pick up any staff folder on disk that the
            # in-memory/cached embeddings don't know about yet. ---
            known_names = set(GLOBAL_DB_EMBEDDINGS.keys())
            on_disk_names = {
                p for p in os.listdir(db_path)
                if os.path.isdir(os.path.join(db_path, p))
            }
            missing = sorted(on_disk_names - known_names)

            if missing:
                print(f"[INFO] Found {len(missing)} staff folder(s) not yet in the face cache - syncing...")
                for person_name in missing:
                    person_dir = os.path.join(db_path, person_name)
                    embeddings = _embed_person_folder(person_dir, person_name)
                    if embeddings:
                        GLOBAL_DB_EMBEDDINGS[person_name] = embeddings
                        print(f"  Synced {person_name}: {len(embeddings)} angle(s)")
                with open(cache_path, 'wb') as f:
                    pickle.dump(GLOBAL_DB_EMBEDDINGS, f)
                print("[INFO] Face cache updated.")

            if GLOBAL_DB_EMBEDDINGS:
                return

            # First-time full build (no cache, nothing loaded above).
            print("[INFO] Building face database (first time)...")
            total_people = 0
            for person_name in sorted(os.listdir(db_path)):
                person_dir = os.path.join(db_path, person_name)
                if os.path.isdir(person_dir):
                    embeddings = _embed_person_folder(person_dir, person_name)
                    if embeddings:
                        GLOBAL_DB_EMBEDDINGS[person_name] = embeddings
                        total_people += 1
                        print(f"  Loaded {person_name}: {len(embeddings)} angle(s)")
            print(f"[INFO] Total registered staff: {total_people}")

            with open(cache_path, 'wb') as f:
                pickle.dump(GLOBAL_DB_EMBEDDINGS, f)
            print("[INFO] Face cache saved.")

        except Exception as e:
            print(f"[ERROR] Failed to initialize InsightFace engine: {e}")


def reset_face_cache():
    """Forces the AI to retrain its memory on the next scan."""
    global GLOBAL_DB_EMBEDDINGS
    with FACE_LOCK:
        GLOBAL_DB_EMBEDDINGS = {}
        cache_path = _face_cache_path()
        if os.path.exists(cache_path):
            os.remove(cache_path)
        initialize_face_engine(REG_PATH)
    print("[INFO] Face cache reloaded with newly registered staff photos.")


def add_single_face_to_cache(person_name, img_path):
    """Instantly adds a single new photo to RAM without rebuilding the whole database."""
    global GLOBAL_INSIGHT_APP, GLOBAL_DB_EMBEDDINGS
    with FACE_LOCK:
        if GLOBAL_INSIGHT_APP is None:
            initialize_face_engine(REG_PATH)
        if person_name not in GLOBAL_DB_EMBEDDINGS:
            GLOBAL_DB_EMBEDDINGS[person_name] = []
        db_img = cv2.imread(img_path)
        if db_img is not None:
            faces = GLOBAL_INSIGHT_APP.get(db_img)
            face = _largest_face(faces)
            if face is not None:
                embedding = _safe_face_embedding(face)
                if embedding is None:
                    print(f"[WARNING] Registration image for {person_name} produced an invalid embedding: {img_path}")
                    return
                GLOBAL_DB_EMBEDDINGS[person_name].append(embedding)
                print(f"[INFO] Injected new angle for {person_name} into RAM!")
                with open(_face_cache_path(), 'wb') as f:
                    pickle.dump(GLOBAL_DB_EMBEDDINGS, f)
            else:
                print(f"[WARNING] Registration image for {person_name} contains no InsightFace-detectable face: {img_path}")


def recognize_face_sync(frame_to_check, db_path=None):
    """Thread-safe synchronous face recognition using robust cosine similarity."""
    global GLOBAL_INSIGHT_APP, GLOBAL_DB_EMBEDDINGS
    db_path = db_path or REG_PATH

    with FACE_LOCK:
        try:
            if GLOBAL_INSIGHT_APP is None or not GLOBAL_DB_EMBEDDINGS:
                initialize_face_engine(db_path)

            if not GLOBAL_DB_EMBEDDINGS:
                print("[AUTH] Face database is empty.")
                return "UNKNOWN"

            faces = GLOBAL_INSIGHT_APP.get(frame_to_check)
            detected_face = _largest_face(faces)
            if detected_face is None:
                print("[AUTH] InsightFace found no face in authentication frame.")
                return "NO_FACE"

            live_embedding = _safe_face_embedding(detected_face)
            if live_embedding is None:
                print("[AUTH] Live face produced an invalid/non-finite embedding.")
                return "UNKNOWN"

            best_match = "UNKNOWN"
            best_similarity = -1.0
            total_saved = 0
            valid_saved = 0
            invalid_saved = 0

            for name, embeddings_list in GLOBAL_DB_EMBEDDINGS.items():
                for saved_embedding in embeddings_list:
                    total_saved += 1
                    saved = np.asarray(saved_embedding, dtype=np.float32).reshape(-1)
                    if (saved.size != live_embedding.size or
                            not np.all(np.isfinite(saved))):
                        invalid_saved += 1
                        continue

                    saved_norm = float(np.linalg.norm(saved))
                    if not np.isfinite(saved_norm) or saved_norm <= 1e-12:
                        invalid_saved += 1
                        continue

                    saved = saved / saved_norm
                    similarity = float(np.dot(live_embedding, saved))
                    if not np.isfinite(similarity):
                        invalid_saved += 1
                        continue

                    valid_saved += 1
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = name

            FACE_MATCH_THRESHOLD = 0.40
            accepted = valid_saved > 0 and best_similarity >= FACE_MATCH_THRESHOLD
            print(
                f"[AUTH] Best face match: {best_match} | "
                f"similarity={best_similarity:.3f} | "
                f"threshold={FACE_MATCH_THRESHOLD:.2f} | "
                f"accepted={accepted} | "
                f"saved={total_saved} valid={valid_saved} invalid={invalid_saved}"
            )

            if valid_saved == 0:
                print("[AUTH] ERROR: zero usable saved embeddings. Delete face_cache.pkl and restart with this file.")

            return best_match if accepted else "UNKNOWN"

        except Exception as e:
            print(f"[ERROR] InsightFace Auth Error: {type(e).__name__}: {e}")
            return "UNKNOWN"


class AIModels:
    """Manages all AI models: YOLO, MediaPipe, InsightFace, and WHO Handwashing."""

    def __init__(self):
        print("[DEBUG] Loading YOLOv8 PPE Model...")
        self.yolo_model = YOLO(env.YOLO_MODEL_PATH)

        print("[DEBUG] Loading MediaPipe Hands...")
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=cfg.get("max_num_hands"),
            min_detection_confidence=cfg.get("hand_detection_confidence"),
            min_tracking_confidence=cfg.get("hand_tracking_confidence"),
        )
        self.mp_draw = mp.solutions.drawing_utils

        print("[DEBUG] Loading MediaPipe Face Detection (Gatekeeper)...")
        self.mp_face = mp.solutions.face_detection
        # Use MediaPipe's full-range face detector when supported.  Some
        # MediaPipe builds differ, so fall back to the original constructor
        # instead of letting face-detector setup prevent the camera worker
        # from starting at all.
        face_conf = cfg.get("face_detection_confidence")
        try:
            self.face_detector = self.mp_face.FaceDetection(
                model_selection=1,
                min_detection_confidence=face_conf,
            )
            print(f"[OK] MediaPipe Face Detection loaded (full-range, conf={face_conf}).")
        except (TypeError, ValueError) as e:
            print(f"[WARN] Full-range MediaPipe face detector unavailable ({e}); using default model.")
            self.face_detector = self.mp_face.FaceDetection(
                min_detection_confidence=face_conf
            )

        self.frame_counter = 0
        self.last_yolo_boxes = []

        # --- WHO HANDWASHING GESTURE CLASSIFIER ---
        self.who_session = None
        model_path = env.WHO_MODEL_PATH
        if os.path.exists(model_path):
            try:
                import onnxruntime as ort
                self.who_session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
                self.who_input_name = self.who_session.get_inputs()[0].name
                print("[OK] WHO Handwashing LSTM loaded successfully!")
            except Exception as e:
                print(f"[WARN] Could not load WHO model: {e}")
        else:
            print(f"[WARN] WHO model not found at {model_path}. Gesture classification disabled.")

        self.prediction_buffer = deque(maxlen=45)
        self.lstm_sequence_buffer = deque(maxlen=30)

        initialize_face_engine(REG_PATH)

    def detect_ppe(self, frame):
        has_mask, has_hat = False, False
        self.frame_counter += 1
        yolo_conf = cfg.get("yolo_conf_threshold")

        if self.frame_counter % 3 == 0 or not self.last_yolo_boxes:
            results = self.yolo_model(frame, stream=True, conf=yolo_conf, verbose=False)
            self.last_yolo_boxes = []
            for r in results:
                for box in r.boxes:
                    self.last_yolo_boxes.append({
                        'xyxy': box.xyxy[0].cpu().numpy(),
                        'cls': int(box.cls[0])
                    })

        for box_data in self.last_yolo_boxes:
            class_id = box_data['cls']
            class_name = self.yolo_model.names[class_id]
            x1, y1, x2, y2 = map(int, box_data['xyxy'])

            color = (0, 255, 0) if class_name == 'mask' else (255, 0, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, class_name.upper(), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if class_name == 'mask':
                has_mask = True
            elif class_name == 'hat':
                has_hat = True

        return frame, has_mask, has_hat

    def detect_face(self, frame_rgb):
        """Fast face-presence gate used before the heavier InsightFace scan.

        MediaPipe already applies its own detection-confidence threshold, so
        do not reject a valid detection just because the face occupies less
        than 10% of a wide-angle camera frame.
        """
        try:
            face_results = self.face_detector.process(frame_rgb)
            return bool(face_results.detections)
        except Exception as e:
            # A transient MediaPipe failure should not kill the camera loop.
            print(f"[WARN] MediaPipe face gate error: {e}")
            return False

    def detect_hands(self, frame_rgb):
        hand_results = self.hands.process(frame_rgb)
        return {
            'detected': bool(hand_results.multi_hand_landmarks),
            'hand_results': hand_results,
            'count': len(hand_results.multi_hand_landmarks) if hand_results.multi_hand_landmarks else 0
        }

    def draw_hand_landmarks(self, frame, hand_results):
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        return frame

    def get_hand_bbox(self, hand_landmarks, frame_w, frame_h):
        x_min = min([lm.x for lm in hand_landmarks.landmark]) * frame_w
        x_max = max([lm.x for lm in hand_landmarks.landmark]) * frame_w
        y_min = min([lm.y for lm in hand_landmarks.landmark]) * frame_h
        y_max = max([lm.y for lm in hand_landmarks.landmark]) * frame_h
        return [x_min, y_min, x_max, y_max]

    @staticmethod
    def bboxes_intersect(box1, box2):
        return not (box1[2] < box2[0] or box1[0] > box2[2] or
                    box1[3] < box2[1] or box1[1] > box2[3])

    def predict_who_step(self, hand_landmarks_data):
        if not self.who_session or not hand_landmarks_data or not hand_landmarks_data.multi_hand_landmarks:
            self.lstm_sequence_buffer.clear()
            return 0

        sorted_hands = sorted(
            hand_landmarks_data.multi_hand_landmarks, key=lambda h: h.landmark[0].x
        )

        current_features = []
        for hand in sorted_hands[:2]:
            wrist = hand.landmark[0]
            middle_base = hand.landmark[9]
            hand_size = math.hypot(wrist.x - middle_base.x, wrist.y - middle_base.y)
            if hand_size == 0:
                hand_size = 1.0
            for lm in hand.landmark:
                current_features.extend([
                    (lm.x - wrist.x) / hand_size,
                    (lm.y - wrist.y) / hand_size,
                    (lm.z - wrist.z) / hand_size
                ])

        while len(current_features) < 126:
            current_features.append(0.0)

        if len(sorted_hands) == 2:
            h1_w, h2_w = sorted_hands[0].landmark[0], sorted_hands[1].landmark[0]
            current_features.append(math.hypot(h1_w.x - h2_w.x, h1_w.y - h2_w.y))
            h1_i, h2_i = sorted_hands[0].landmark[8], sorted_hands[1].landmark[8]
            current_features.append(math.hypot(h1_i.x - h2_i.x, h1_i.y - h2_i.y))
        else:
            current_features.extend([1.0, 1.0])

        self.lstm_sequence_buffer.append(current_features)

        if len(self.lstm_sequence_buffer) < 30:
            return 0

        seq_array = np.array([list(self.lstm_sequence_buffer)], dtype=np.float32)
        logits = self.who_session.run(None, {self.who_input_name: seq_array})[0]
        pred = int(np.argmax(logits, axis=1)[0])

        self.prediction_buffer.append(pred)
        most_common = Counter(self.prediction_buffer).most_common(1)[0][0]
        return most_common

    def get_smoothed_step(self):
        if not self.prediction_buffer:
            return 0
        most_common_step, _ = Counter(self.prediction_buffer).most_common(1)[0]
        return most_common_step

    def clear_buffer(self):
        self.prediction_buffer.clear()

    def cleanup(self):
        self.hands.close()
        self.face_detector.close()