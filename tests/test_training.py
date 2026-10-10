"""
CT pipeline tests on a tiny synthetic AutoVI-style dataset (no real data or
model files needed, so they run in CI).
"""
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest

from core.inference import run_inference
from training.common import (
    assert_no_duplicates, dice_iou, image_metrics, make_splits, preprocess_like_app,
)
from training.evaluate import gate


def write_png(path, rng, shape=(40, 40, 3)):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), rng.integers(0, 256, size=shape, dtype=np.uint8))


@pytest.fixture
def autovi_dir(tmp_path):
    rng = np.random.default_rng(0)
    for i in range(20):
        write_png(tmp_path / 'train' / 'good' / f'{i:04d}.png', rng)
    for i in range(12):
        write_png(tmp_path / 'test' / 'good' / f'{i:04d}.png', rng)
    for i in range(10):
        write_png(tmp_path / 'test' / 'missing' / f'{i:04d}.png', rng)
        mask = np.zeros((40, 40), dtype=np.uint8)
        mask[10:20, 10:20] = 255
        mask_path = tmp_path / 'ground_truth' / 'missing' / f'{i:04d}' / '0000.png'
        mask_path.parent.mkdir(parents=True)
        cv2.imwrite(str(mask_path), mask)
    return tmp_path


def names(items):
    return sorted(p for p, _ in items)


def test_split_is_deterministic(autovi_dir):
    assert make_splits(str(autovi_dir)) == make_splits(str(autovi_dir))


def test_split_is_disjoint_and_complete(autovi_dir):
    splits = make_splits(str(autovi_dir))
    all_images = names(splits['train']) + names(splits['val']) + names(splits['test'])
    assert len(all_images) == len(set(all_images)) == 20 + 12 + 10
    # test/good is used only for testing
    assert sum(m is None for _, m in splits['test']) == 12
    # missing images split 60 / 20 / 20
    assert [sum(m is not None for _, m in splits[s]) for s in ('train', 'val', 'test')] == [6, 2, 2]


def test_copied_train_missing_folder_is_ignored(autovi_dir):
    shutil.copytree(autovi_dir / 'test' / 'missing', autovi_dir / 'train' / 'missing')
    splits = make_splits(str(autovi_dir))
    used_folders = {Path(p).parent.parts[-2:] for items in splits.values() for p, _ in items}
    assert ('train', 'missing') not in used_folders
    assert_no_duplicates(splits)


def test_duplicate_image_across_splits_is_detected(autovi_dir):
    shutil.copy(autovi_dir / 'test' / 'good' / '0000.png', autovi_dir / 'train' / 'good' / 'leak.png')
    with pytest.raises(AssertionError, match='leakage'):
        assert_no_duplicates(make_splits(str(autovi_dir)))


class CapturingModel:
    def __init__(self):
        self.last_input = None

    def predict(self, x, verbose=0):
        self.last_input = x
        return np.zeros((1, 128, 128, 1), dtype='float32')


def test_training_preprocessing_matches_app():
    img = np.random.default_rng(1).integers(0, 256, size=(300, 200, 3), dtype=np.uint8)
    model = CapturingModel()
    run_inference(img, model)
    np.testing.assert_array_equal(model.last_input[0], preprocess_like_app(img))


def test_run_inference_returns_mask_at_original_size():
    img = np.zeros((300, 200, 3), dtype=np.uint8)
    out = run_inference(img, CapturingModel())
    assert out['mask'].shape == (300, 200)


def test_image_metrics():
    m = image_metrics([1, 1, 0, 0, 0], [1, 0, 0, 0, 1])
    assert (m['TP'], m['FN'], m['TN'], m['FP']) == (1, 1, 2, 1)
    assert m['recall'] == 0.5
    assert m['specificity'] == pytest.approx(2 / 3)


def test_dice_iou():
    a = np.zeros((10, 10)); a[:5] = 1
    b = np.zeros((10, 10)); b[:, :5] = 1
    dice, iou = dice_iou(a, b)
    assert dice == pytest.approx(0.5)
    assert iou == pytest.approx(25 / 75)


def test_gate_rejects_candidate_that_flags_everything():
    current = {'recall': 0.95, 'specificity': 1.0, 'dice_mean': 0.88}
    candidate = {'recall': 1.0, 'specificity': 0.0, 'dice_mean': 0.36}
    passed, checks = gate(current, candidate, dice_tolerance=0.02)
    assert not passed
    assert checks == {'recall': True, 'specificity': False, 'dice_mean': False}


def test_gate_allows_small_dice_noise():
    current = {'recall': 0.95, 'specificity': 1.0, 'dice_mean': 0.88}
    candidate = {'recall': 0.95, 'specificity': 1.0, 'dice_mean': 0.87}
    assert gate(current, candidate, dice_tolerance=0.02)[0]


def test_r2unet_output_shape():
    from training.r2unet import build_r2unet
    model = build_r2unet((32, 32, 3), base_filters=4, t=2)
    assert model.output_shape == (None, 32, 32, 1)
