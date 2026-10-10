# Training / CT pipeline

Retrains the R2U-Net and decides, automatically, whether the new model is at
least as good as the one in production. Same code as the training notebook in
`D:\MODEL R2U-NET` that produced `models/defect_model.h5`.

| File | What it does |
|---|---|
| `common.py` | Dataset split, loading, metrics. Split is identical to the notebook (same seed → same files) |
| `r2unet.py` | R2U-Net architecture (recurrent conv with shared weights, residual, BN per step, 5 levels) |
| `retrain.py` | Trains a candidate model and saves it as `.h5` (128x128, same format the app loads) |
| `evaluate.py` | The gate: runs current and candidate through the app's own `core/inference.py` on the test split |

## Data split (no leakage)

| Split | good | missing |
|---|---|---|
| train | `train/good` 85% | `test/missing` 60% |
| val | `train/good` 15% | `test/missing` 20% |
| test | **all of `test/good`** | `test/missing` 20% |

Every image is MD5-checked: if the same file appears in two splits the run
stops. A copied `train/missing` folder (identical to `test/missing`) is ignored.

## Expected data layout

One AutoVI category folder, unchanged:

```
<data-dir>/
├── train/good/*.png
├── test/good/*.png
├── test/missing/XXXX.png
├── ground_truth/missing/XXXX/0000.png   ← mask of test/missing/XXXX.png
└── license.txt                          (AutoVI: CC BY-NC-SA 4.0, Renault Group)
```

In CI, `retrain.yml` downloads `<model_target>_dataset.zip`
(`defect_dataset.zip` or `tank_screw_dataset.zip`) from the `dataset-v1`
GitHub Release and unzips it to `training/data/<model_target>/`, so
`train/`, `test/` and `ground_truth/` must be at the top level of the zip.
`training/data/` and `training/output/` are git-ignored.

## The gate

Run with the app's default settings (Confidence 0.35, Pixel Threshold 500).
The candidate passes only if it is not worse than the current model on:

- **Recall** — missing parts caught
- **Specificity** — good parts passed
- **Mean Dice** on test images with a defect (allowed to be up to 0.02 lower)

Checking recall alone is not enough: a badly trained model that flags every
part as MISSING gets 100% recall. Specificity catches that.

## Running locally

```bash
python training/retrain.py --data-dir "D:/MODEL R2U-NET/pipe_staple" --output training/output/candidate_defect_model.h5
python training/evaluate.py --current models/defect_model.h5 --candidate training/output/candidate_defect_model.h5 --data-dir "D:/MODEL R2U-NET/pipe_staple"
```

`retrain.py --epochs 2` is enough to check that everything runs.
