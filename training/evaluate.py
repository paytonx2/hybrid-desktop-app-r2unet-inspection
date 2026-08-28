"""
Compares a "candidate" model against the currently-deployed model on a
held-out validation set, using the SAME dice_coeff used everywhere else
in the project (imported, not re-implemented, so it can never drift).

This is the automated "gate" of the CT pipeline: a candidate model is only
allowed to become a release candidate if it scores at least as well as the
current one. A human still approves the actual release (see README).

Usage:
    python training/evaluate.py \
        --current models/defect_model.h5 \
        --candidate training/output/candidate_model.h5 \
        --val-dir training/data/val
"""
import argparse
import os
import sys

import numpy as np
import tensorflow as tf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.losses import CUSTOM_OBJECTS, dice_coeff  # noqa: E402


def load_validation_set(val_dir):
    """
    Expects:
        val_dir/images/*.png   (RGB, any size)
        val_dir/masks/*.png    (single channel, same filenames as images)
    Resizes everything to 128x128 to match the model's input, exactly like
    core/inference.py does at inference time.
    """
    import cv2

    images_dir = os.path.join(val_dir, 'images')
    masks_dir = os.path.join(val_dir, 'masks')

    if not os.path.isdir(images_dir) or not os.path.isdir(masks_dir):
        raise FileNotFoundError(
            f"Expected {images_dir} and {masks_dir} to exist. "
            f"See training/README.md for the expected validation set layout."
        )

    filenames = sorted(os.listdir(images_dir))
    if not filenames:
        raise ValueError(f"No validation images found in {images_dir}")

    xs, ys = [], []
    for fname in filenames:
        img = cv2.imread(os.path.join(images_dir, fname))
        mask = cv2.imread(os.path.join(masks_dir, fname), cv2.IMREAD_GRAYSCALE)
        if img is None or mask is None:
            continue
        img = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (128, 128)).astype('float32') / 255.0
        mask = cv2.resize(mask, (128, 128)).astype('float32') / 255.0
        mask = np.expand_dims(mask, axis=-1)
        xs.append(img)
        ys.append(mask)

    return np.array(xs), np.array(ys)


def score_model(model_path, x_val, y_val):
    model = tf.keras.models.load_model(model_path, custom_objects=CUSTOM_OBJECTS, compile=False)
    preds = model.predict(x_val, verbose=0)
    return float(dice_coeff(y_val.astype('float32'), preds.astype('float32')).numpy())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--current', required=True, help='Path to the model currently in production')
    parser.add_argument('--candidate', required=True, help='Path to the newly retrained model')
    parser.add_argument('--val-dir', required=True, help='Validation set directory (see training/README.md)')
    parser.add_argument('--min-improvement', type=float, default=0.0,
                         help='Candidate must score at least this much higher than current (default: 0.0, i.e. must not be worse)')
    args = parser.parse_args()

    x_val, y_val = load_validation_set(args.val_dir)
    print(f"Validation set: {len(x_val)} image/mask pairs")

    current_score = score_model(args.current, x_val, y_val)
    candidate_score = score_model(args.candidate, x_val, y_val)

    print(f"Current model dice score:   {current_score:.4f}")
    print(f"Candidate model dice score: {candidate_score:.4f}")

    passed = candidate_score >= current_score + args.min_improvement
    print(f"GATE: {'PASSED' if passed else 'FAILED'}")

    # Machine-readable summary for the GitHub Actions workflow to read
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        with open(summary_path, 'a') as f:
            f.write("## CT Evaluation Gate\n")
            f.write(f"- Current model dice score: `{current_score:.4f}`\n")
            f.write(f"- Candidate model dice score: `{candidate_score:.4f}`\n")
            f.write(f"- Result: **{'PASSED ✅' if passed else 'FAILED ❌'}**\n")

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
