import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from core.inference import run_inference


class BatchImageWorker(QThread):
    """
    ประมวลผลรปูภาพหลายไฟลพ์ รอ้ มกนั (แบบเรยีงทลีะภาพใน thread แยก)
    result_ready ส่ง: index, file_path, result_bgr, status, pixel_count
    """
    result_ready = Signal(int, str, object, str, int)
    error = Signal(int, str, str)  # index, file_path, message
    finished_batch = Signal()

    def __init__(self, file_paths, model_manager, model_type, conf_threshold, px_threshold, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.model_manager = model_manager
        self.model_type = model_type
        self.conf_threshold = conf_threshold
        self.px_threshold = px_threshold
        self._stop = False

    def run(self):
        model = self.model_manager.get_model(self.model_type)
        for idx, path in enumerate(self.file_paths):
            if self._stop:
                break
            try:
                # รองรับ path ทมี่ อีกัขระภาษาไทย/ยนูโิคด้
                img_array = np.fromfile(path, dtype=np.uint8)
                img_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img_bgr is None:
                    self.error.emit(idx, path, "Unable to read this image file")
                    continue

                out = run_inference(img_bgr, model, self.conf_threshold, self.px_threshold)
                self.result_ready.emit(idx, path, out['result_bgr'], out['status'], out['pixel_count'])
            except Exception as e:
                self.error.emit(idx, path, str(e))

        self.finished_batch.emit()

    def stop(self):
        self._stop = True
