"""
run_inference with a fake model, so these tests don't need the real .h5 files
(which are not in git) and run fast in CI.
"""
import numpy as np

from core.inference import run_inference


class FakeModel:
    """Returns a fixed 128x128 probability mask, like a keras model would."""

    def __init__(self, mask):
        self.mask = mask
        self.last_input = None

    def predict(self, x, verbose=0):
        self.last_input = x
        return self.mask[np.newaxis, :, :, np.newaxis]


def blank_image(h=256, w=256):
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_preprocessing_matches_model_input():
    model = FakeModel(np.zeros((128, 128), dtype='float32'))
    run_inference(blank_image(300, 200), model)
    assert model.last_input.shape == (1, 128, 128, 3)
    assert model.last_input.dtype == np.float32


def test_empty_mask_is_good():
    model = FakeModel(np.zeros((128, 128), dtype='float32'))
    out = run_inference(blank_image(), model, conf_threshold=0.35, px_threshold=500)
    assert out['status'] == "GOOD"
    assert out['pixel_count'] == 0
    assert out['result_bgr'].shape == (256, 256, 3)


def test_large_defect_is_missing():
    mask = np.zeros((128, 128), dtype='float32')
    mask[32:96, 32:96] = 0.9  # 64x64 at 128 -> 128x128 = 16384 px at 256
    out = run_inference(blank_image(), FakeModel(mask), conf_threshold=0.35, px_threshold=500)
    assert out['status'] == "MISSING"
    assert out['pixel_count'] == 128 * 128


def test_confidence_threshold_filters_weak_predictions():
    mask = np.full((128, 128), 0.3, dtype='float32')
    out = run_inference(blank_image(), FakeModel(mask), conf_threshold=0.35, px_threshold=500)
    assert out['pixel_count'] == 0
    assert out['status'] == "GOOD"
