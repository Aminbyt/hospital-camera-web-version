"""Sink Calibration - auto-detection algorithm identical to the original
desktop sink_calibration.py. The interactive PyQt ROIDrawer/dialog is gone -
manual ROI drawing now happens in the browser (see
frontend/src/components/RoiDrawer.jsx) which POSTs normalized [x1,y1,x2,y2]
coordinates straight to PATCH /api/cameras/{id}."""

import cv2
import numpy as np


class SinkCalibration:

    @staticmethod
    def auto_detect_sink_line(frame):
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        crop_start = int(h * 0.4)
        crop_end = int(h * 0.95)
        roi = gray[crop_start:crop_end, :]

        blurred = cv2.GaussianBlur(roi, (7, 7), 0)
        edges = cv2.Canny(blurred, 30, 100)

        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100,
            minLineLength=int(w * 0.3), maxLineGap=50
        )

        best_y = None
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi)
                if angle < 15 or angle > 165:
                    actual_y = y1 + crop_start
                    if best_y is None or actual_y < best_y:
                        best_y = actual_y

        return best_y

    @staticmethod
    def calculate_sink_y_start(detected_y, frame_h):
        if detected_y is not None:
            elbow_offset = int(frame_h * 0.15)
            return max(0, detected_y - elbow_offset)
        else:
            return int(frame_h * 0.65)

    @staticmethod
    def draw_sink_zone(frame, sink_y_start, manual=False):
        frame_h, frame_w = frame.shape[:2]
        cv2.line(frame, (0, sink_y_start), (frame_w, sink_y_start), (0, 0, 255), 2)
        zone_type = "MANUAL" if manual else "AUTO"
        cv2.putText(frame, f"VALID ZONE ({zone_type})", (10, sink_y_start - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        return frame

    @staticmethod
    def draw_manual_roi(frame, roi):
        if roi:
            frame_h, frame_w = frame.shape[:2]
            rx1 = int(roi[0] * frame_w)
            ry1 = int(roi[1] * frame_h)
            rx2 = int(roi[2] * frame_w)
            ry2 = int(roi[3] * frame_h)
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)
            cv2.putText(frame, "VALID ZONE (MANUAL)", (rx1, ry1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        return frame
