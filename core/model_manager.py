import os
import tensorflow as tf

from core.losses import CUSTOM_OBJECTS


class ModelManager:
    """
    โหลดโมเดลทงั้ 2 ตวั ครัง้เดยี วตอนเปิดโปรแกรม แลว้เกบ็ ไวใ้นหน่วยความจำ
    เพอื่ ใหก้ ารตรวจจับแบบ real-time ไมต่ อ้ งโหลดโมเดลซำ้ ทกุ ครัง้
    """

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.defect_model = None
        self.screw_model = None
        self._loaded = False

    def default_paths(self):
        defect_path = os.path.join(self.base_dir, 'models', 'defect_model.h5')
        screw_path = os.path.join(self.base_dir, 'models', 'r2unet__model_underbody_screw.h5')
        return defect_path, screw_path

    def load_models(self, defect_path=None, screw_path=None, progress_callback=None):
        defect_path = defect_path or self.default_paths()[0]
        screw_path = screw_path or self.default_paths()[1]

        if not os.path.exists(defect_path):
            raise FileNotFoundError(f"Model file not found: {defect_path}")
        if not os.path.exists(screw_path):
            raise FileNotFoundError(f"Model file not found: {screw_path}")

        if progress_callback:
            progress_callback("Loading Pipe Staple model...")
        self.defect_model = self._load_h5(defect_path)

        if progress_callback:
            progress_callback("Loading Underbody Screw model...")
        self.screw_model = self._load_h5(screw_path)

        self._loaded = True
        if progress_callback:
            progress_callback("All models loaded successfully")

    @staticmethod
    def _load_h5(path):
        try:
            return tf.keras.models.load_model(
                path, custom_objects=CUSTOM_OBJECTS, compile=False
            )
        except TypeError as e:
            if "batch_shape" in str(e):
                raise RuntimeError(
                    "This .h5 file was saved with a newer Keras version (Keras 3 format), "
                    "but the installed TensorFlow is too old to read it. "
                    "Please run: pip install --upgrade tensorflow  (requires tensorflow>=2.16) "
                    "and restart the app."
                ) from e
            raise

    def is_loaded(self):
        return self._loaded

    def get_model(self, model_type):
        if model_type == "tank_screw":
            return self.screw_model
        return self.defect_model  # default = "defect"
