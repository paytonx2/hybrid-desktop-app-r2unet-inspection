import time
import cv2
from PySide6.QtCore import QThread, Signal

from core.inference import run_inference


def list_available_cameras(max_test=5):
    """Scan for cameras connected to this machine (index 0..max_test-1)"""
    available = []
    for i in range(max_test):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if hasattr(cv2, 'CAP_DSHOW') else cv2.VideoCapture(i)
        if cap is not None and cap.isOpened():
            available.append(i)
            cap.release()
    return available


class CameraWorker(QThread):
    """
    รันอยใู่ น thread แยก เพอื่ ไมใ่ หห้ นา้ตา (UI) กระตกุ ระหวา่ งอา่ นภาพจากกลอ้ ง/วดิโีอ
    หรอื ระหวา่ งรัน AI inference

    frame_ready ส่ง: raw_bgr, result_bgr (หรอื None), status (หรอื None), pixel_count (หรอื None)
    """
    frame_ready = Signal(object, object, object, object)
    error = Signal(str)
    finished_stream = Signal()

    def __init__(self, source, model_manager, parent=None):
        super().__init__(parent)
        self.source = source  # int = camera index, str = video file path
        self.model_manager = model_manager
        self._running = False

        self.ai_enabled = False
        self.model_type = 'defect'
        self.conf_threshold = 0.35
        self.px_threshold = 500

    def run(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self.error.emit("Unable to open the camera/video. Please check the device or file.")
            return

        self._running = True
        is_video_file = isinstance(self.source, str)

        while self._running:
            ret, frame = cap.read()
            if not ret:
                if is_video_file:
                    # Loop the video when it reaches the end
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break

            result_bgr, status, pixel_count = None, None, None
            if self.ai_enabled and self.model_manager.is_loaded():
                try:
                    model = self.model_manager.get_model(self.model_type)
                    out = run_inference(frame, model, self.conf_threshold, self.px_threshold)
                    result_bgr = out['result_bgr']
                    status = out['status']
                    pixel_count = out['pixel_count']
                except Exception as e:
                    self.error.emit(f"Error during analysis: {e}")

            self.frame_ready.emit(frame, result_bgr, status, pixel_count)

            if not self.ai_enabled:
                time.sleep(0.03)

        cap.release()
        self.finished_stream.emit()

    def stop(self):
        self._running = False
        self.wait(3000)
