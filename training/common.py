"""
Shared pieces of the CT pipeline: dataset split, image loading and metrics.

The split logic is identical to the training notebook (D:\\MODEL R2U-NET), so
with the same seed and dataset it produces exactly the same train / val / test
files. Preprocessing mirrors core/inference.py, and evaluate.py runs the real
core.inference.run_inference, so the numbers measured here are the numbers the
desktop app produces.

Expected dataset layout (one AutoVI category, e.g. pipe_staple):
    data_dir/train/good/*.png
    data_dir/test/good/*.png
    data_dir/test/missing/XXXX.png
    data_dir/ground_truth/missing/XXXX/0000.png   (mask of test/missing/XXXX.png)
Any other folder (such as a copied train/missing) is ignored on purpose.
"""
import hashlib
import os
from glob import glob

import cv2
import numpy as np

IMG_SIZE = 128            # must match core/inference.py
SEED = 42
MISSING_SPLIT = (0.6, 0.2, 0.2)   # missing images: train / val / test
GOOD_VAL_FRACTION = 0.15          # part of train/good used for validation


def read_image(path, flags=cv2.IMREAD_COLOR):
    # np.fromfile + imdecode handles Thai characters / spaces in paths
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), flags)


def preprocess_like_app(img_bgr, img_size=IMG_SIZE):
    """Same steps as core/inference.py: BGR -> RGB -> resize -> / 255."""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_input = cv2.resize(img_rgb, (img_size, img_size))
    return img_input.astype('float32') / 255.0


def load_mask(path, img_size=IMG_SIZE):
    if path is None:
        return np.zeros((img_size, img_size, 1), dtype='float32')
    m = read_image(path, cv2.IMREAD_GRAYSCALE)
    m = cv2.resize(m, (img_size, img_size), interpolation=cv2.INTER_NEAREST)
    return (m > 0).astype('float32')[..., None]


def gt_path_for(data_dir, img_path):
    name = os.path.splitext(os.path.basename(img_path))[0]
    return os.path.join(data_dir, 'ground_truth', 'missing', name, '0000.png')


def make_splits(data_dir, seed=SEED):
    """
    Returns {"train": [...], "val": [...], "test": [...]}, each a list of
    (image_path, mask_path_or_None). test/good is used for testing only.
    """
    good_train_all = sorted(glob(os.path.join(data_dir, 'train', 'good', '*.png')))
    good_test = sorted(glob(os.path.join(data_dir, 'test', 'good', '*.png')))
    missing_all = sorted(glob(os.path.join(data_dir, 'test', 'missing', '*.png')))
    missing_all = [p for p in missing_all if os.path.exists(gt_path_for(data_dir, p))]

    if not good_train_all or not good_test or not missing_all:
        raise FileNotFoundError(
            f"{data_dir} must contain train/good, test/good, test/missing and "
            f"ground_truth/missing (AutoVI layout, see training/README.md)"
        )

    rng = np.random.default_rng(seed)

    missing_perm = list(rng.permutation(missing_all))
    n_tr = int(round(MISSING_SPLIT[0] * len(missing_perm)))
    n_val = int(round(MISSING_SPLIT[1] * len(missing_perm)))
    missing_train = sorted(missing_perm[:n_tr])
    missing_val = sorted(missing_perm[n_tr:n_tr + n_val])
    missing_test = sorted(missing_perm[n_tr + n_val:])

    good_perm = list(rng.permutation(good_train_all))
    n_good_val = int(round(GOOD_VAL_FRACTION * len(good_perm)))
    good_val = sorted(good_perm[:n_good_val])
    good_train = sorted(good_perm[n_good_val:])

    def with_masks(paths):
        return [(str(p), gt_path_for(data_dir, p)) for p in paths]

    return {
        'train': [(str(p), None) for p in good_train] + with_masks(missing_train),
        'val': [(str(p), None) for p in good_val] + with_masks(missing_val),
        'test': [(str(p), None) for p in good_test] + with_masks(missing_test),
    }


def assert_no_duplicates(splits):
    """Fails if the same image file (by MD5) appears in more than one split."""
    seen = {}
    for split_name, items in splits.items():
        for img_path, _ in items:
            with open(img_path, 'rb') as f:
                h = hashlib.md5(f.read()).hexdigest()
            if h in seen and seen[h][0] != split_name:
                raise AssertionError(
                    f"Data leakage: {img_path} ({split_name}) is identical to {seen[h][1]} ({seen[h][0]})"
                )
            seen.setdefault(h, (split_name, img_path))
    return len(seen)


def split_summary(splits):
    return {name: {'good': sum(m is None for _, m in items),
                   'missing': sum(m is not None for _, m in items)}
            for name, items in splits.items()}


def load_split(items, img_size=IMG_SIZE):
    X = np.stack([preprocess_like_app(read_image(p), img_size) for p, _ in items])
    Y = np.stack([load_mask(m, img_size) for _, m in items])
    return X, Y


def image_metrics(y_true, y_pred):
    """y_true / y_pred: arrays of 0 (GOOD) / 1 (MISSING)."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {'TP': tp, 'FN': fn, 'TN': tn, 'FP': fp,
            'accuracy': (tp + tn) / len(y_true) if len(y_true) else 0.0,
            'precision': precision, 'recall': recall,
            'specificity': specificity, 'f1': f1}


def dice_iou(gt_mask, pred_mask):
    """Binary masks of the same shape; returns (dice, iou)."""
    gt, pred = gt_mask > 0, pred_mask > 0
    inter = np.logical_and(gt, pred).sum()
    total = gt.sum() + pred.sum()
    union = total - inter
    dice = 2 * inter / total if total else 1.0
    iou = inter / union if union else 1.0
    return float(dice), float(iou)
