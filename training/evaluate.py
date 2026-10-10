"""
CT evaluation gate: compares a candidate model against the production model on
the held-out test split, using the app's own code end to end:
    - models are loaded with core.model_manager (same as the app)
    - every test image goes through core.inference.run_inference with the
      app's Confidence / Pixel Threshold, giving GOOD / MISSING exactly as the
      app would show it

The gate passes only if the candidate is not worse than the current model:
    recall      (missing parts caught)       >= current
    specificity (good parts passed)          >= current
    mean Dice   (on test images with defect) >= current - dice tolerance

A human still decides whether to release the candidate (see CICTCD_SETUP.md).

Usage:
    python training/evaluate.py \
        --current models/defect_model.h5 \
        --candidate training/output/candidate_defect_model.h5 \
        --data-dir training/data/defect
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.inference import run_inference  # noqa: E402
from core.model_manager import ModelManager  # noqa: E402
from training.common import SEED, dice_iou, image_metrics, make_splits, read_image  # noqa: E402


def evaluate_model(model_path, test_items, conf, px):
    model = ModelManager._load_h5(model_path)
    y_true, y_pred, dices, ious = [], [], [], []
    for img_path, mask_path in test_items:
        out = run_inference(read_image(img_path), model, conf, px)
        y_true.append(0 if mask_path is None else 1)
        y_pred.append(1 if out['status'] == 'MISSING' else 0)
        if mask_path is not None:
            d, i = dice_iou(read_image(mask_path, flags=0), out['mask'])
            dices.append(d)
            ious.append(i)
    result = image_metrics(y_true, y_pred)
    result.update({'dice_mean': float(np.mean(dices)), 'dice_std': float(np.std(dices)),
                   'iou_mean': float(np.mean(ious)), 'defect_images': len(dices)})
    return result


def gate(current, candidate, dice_tolerance):
    checks = {
        'recall': candidate['recall'] >= current['recall'],
        'specificity': candidate['specificity'] >= current['specificity'],
        'dice_mean': candidate['dice_mean'] >= current['dice_mean'] - dice_tolerance,
    }
    return all(checks.values()), checks


def format_table(current, candidate, checks):
    rows = [('Recall (missing caught)', 'recall', 'TP', 'FN'),
            ('Specificity (good passed)', 'specificity', 'TN', 'FP'),
            ('Precision', 'precision', None, None),
            ('Mean Dice (defect images)', 'dice_mean', None, None),
            ('Mean IoU (defect images)', 'iou_mean', None, None)]
    lines = ['| Metric | Current | Candidate | Gate |', '|---|---|---|---|']
    for label, key, a, b in rows:
        def cell(r):
            extra = f" ({r[a]}/{r[a] + r[b]})" if a else ''
            return f"{r[key]:.4f}{extra}"
        mark = ('pass' if checks[key] else 'FAIL') if key in checks else ''
        lines.append(f"| {label} | {cell(current)} | {cell(candidate)} | {mark} |")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--current', required=True, help='Model currently in production')
    parser.add_argument('--candidate', required=True, help='Newly retrained model')
    parser.add_argument('--data-dir', required=True, help='Same AutoVI category folder used by retrain.py')
    parser.add_argument('--seed', type=int, default=SEED, help='Must match retrain.py so the test split is the same')
    parser.add_argument('--conf', type=float, default=0.35, help='App Confidence setting')
    parser.add_argument('--px', type=int, default=500, help='App Pixel Threshold setting')
    parser.add_argument('--dice-tolerance', type=float, default=0.02)
    parser.add_argument('--report', help='Optional path to write the results as JSON')
    args = parser.parse_args()

    test_items = make_splits(args.data_dir, seed=args.seed)['test']
    n_missing = sum(m is not None for _, m in test_items)
    print(f"Test set: {len(test_items)} images ({len(test_items) - n_missing} good, {n_missing} missing), "
          f"conf={args.conf}, px={args.px}")

    current = evaluate_model(args.current, test_items, args.conf, args.px)
    candidate = evaluate_model(args.candidate, test_items, args.conf, args.px)
    passed, checks = gate(current, candidate, args.dice_tolerance)

    table = format_table(current, candidate, checks)
    print(table)
    print(f"GATE: {'PASSED' if passed else 'FAILED'}")

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump({'passed': passed, 'checks': checks, 'current': current, 'candidate': candidate,
                       'settings': vars(args)}, f, indent=2)

    # Shown on the GitHub Actions run page
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        with open(summary_path, 'a', encoding='utf-8') as f:
            f.write("## CT Evaluation Gate\n\n")
            f.write(f"Test set: {len(test_items)} images ({n_missing} missing), "
                    f"app settings conf={args.conf}, px={args.px}\n\n")
            f.write(table + "\n\n")
            f.write(f"**Result: {'PASSED' if passed else 'FAILED'}**\n")

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
