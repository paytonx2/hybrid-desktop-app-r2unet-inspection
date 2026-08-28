# Training / CT pipeline

This folder is a **scaffold**, not a finished retraining pipeline — the
original training code for `defect_model.h5` and
`r2unet__model_underbody_screw.h5` wasn't part of this project, so
`retrain.py` ships with a placeholder tiny model and TODO markers instead
of guessing at your real R2U-Net architecture.

## What's real vs. placeholder

| File | Status |
|---|---|
| `evaluate.py` | Real and working. Loads two `.h5` models, scores both against a validation set using the exact `dice_coeff` from `core/losses.py`, and fails (exit code 1) if the candidate is worse. This is what `retrain.yml` uses as the automated gate. |
| `retrain.py` | Scaffold. `build_model()` and `load_training_data()` are marked `TODO` — replace them with your real R2U-Net architecture and dataset loader. |

## Expected data layout

Both scripts expect this structure:

```
training/data/train/
├── images/
│   ├── 0001.png
│   └── ...
└── masks/
    ├── 0001.png   (same filename as the matching image, grayscale mask)
    └── ...

training/data/val/
├── images/
└── masks/
```

This folder is git-ignored (see `.gitignore`) — datasets don't belong in
git history. Fetch it from wherever you're storing your real dataset
(Supabase Storage, Google Drive, DVC, etc.) as the first step of
`retrain.yml`.

## Running locally

```bash
python training/retrain.py --train-dir training/data/train --output training/output/candidate_defect_model.h5
python training/evaluate.py --current models/defect_model.h5 --candidate training/output/candidate_defect_model.h5 --val-dir training/data/val
```
