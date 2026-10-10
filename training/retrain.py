"""
"Continuous Training" step: trains a candidate R2U-Net on one AutoVI category.

Same pipeline as the training notebook (D:\\MODEL R2U-NET) that produced
models/defect_model.h5: leakage-free train / val / test split, preprocessing
identical to the app, light augmentation, combined BCE + Dice loss from
core/losses.py, EarlyStopping that restores the best epoch.

The test split is never touched here; training/evaluate.py uses it to compare
the candidate against the production model.

Usage:
    python training/retrain.py --data-dir training/data/defect \
                               --output training/output/candidate_defect_model.h5
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.losses import combined_loss, dice_coeff  # noqa: E402  (kept identical to inference)
from training.common import (  # noqa: E402
    IMG_SIZE, SEED, assert_no_duplicates, load_split, make_splits, split_summary,
)


def build_train_dataset(X, Y, batch_size, seed):
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers

    # The camera does not move: only small shifts / rotation, no flips.
    geo_augment = keras.Sequential([
        layers.RandomTranslation(0.05, 0.05, fill_mode='reflect', seed=seed),
        layers.RandomRotation(3 / 360, fill_mode='reflect', seed=seed),
    ])

    def augment(img, mask):
        stacked = geo_augment(tf.concat([img, mask], axis=-1), training=True)  # image + mask together
        img, mask = stacked[..., :3], stacked[..., 3:]
        mask = tf.cast(mask > 0.5, tf.float32)
        img = tf.image.random_brightness(img, 0.08)
        img = tf.image.random_contrast(img, 0.9, 1.1)
        return tf.clip_by_value(img, 0.0, 1.0), mask

    return (tf.data.Dataset.from_tensor_slices((X, Y))
            .shuffle(len(X), seed=seed, reshuffle_each_iteration=True)
            .map(augment, num_parallel_calls=tf.data.AUTOTUNE)
            .batch(batch_size)
            .prefetch(tf.data.AUTOTUNE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True, help='One AutoVI category folder (see training/README.md)')
    parser.add_argument('--output', required=True, help='Where to save the candidate .h5 model')
    parser.add_argument('--epochs', type=int, default=80, help='Upper limit; EarlyStopping usually stops earlier')
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--learning-rate', type=float, default=1e-3)
    parser.add_argument('--base-filters', type=int, default=16)
    parser.add_argument('--seed', type=int, default=SEED)
    args = parser.parse_args()

    import tensorflow as tf
    from tensorflow import keras
    from training.r2unet import build_r2unet

    keras.utils.set_random_seed(args.seed)
    out_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(out_dir, exist_ok=True)

    splits = make_splits(args.data_dir, seed=args.seed)
    n_unique = assert_no_duplicates(splits)
    print(f"Split (no duplicates across {n_unique} images): {split_summary(splits)}")
    with open(os.path.join(out_dir, 'split.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['split', 'image', 'mask'])
        writer.writerows((s, p, m or '') for s, items in splits.items() for p, m in items)

    X_train, Y_train = load_split(splits['train'])
    X_val, Y_val = load_split(splits['val'])
    train_ds = build_train_dataset(X_train, Y_train, args.batch_size, args.seed)
    val_ds = tf.data.Dataset.from_tensor_slices((X_val, Y_val)).batch(args.batch_size)

    model = build_r2unet((IMG_SIZE, IMG_SIZE, 3), base_filters=args.base_filters)
    model.compile(optimizer=keras.optimizers.Adam(args.learning_rate), loss=combined_loss, metrics=[dice_coeff])
    print(f"R2U-Net parameters: {model.count_params():,}")

    callbacks = [
        keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=6, min_lr=1e-6, verbose=1),
        keras.callbacks.EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1),
        keras.callbacks.CSVLogger(os.path.join(out_dir, 'history.csv')),
    ]
    t0 = time.time()
    history = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks, verbose=2)
    best_epoch = int(min(range(len(history.history['val_loss'])), key=history.history['val_loss'].__getitem__)) + 1
    print(f"Trained {len(history.history['val_loss'])} epochs in {(time.time() - t0) / 60:.1f} min "
          f"(best epoch {best_epoch})")

    model.save(args.output)
    print(f"Candidate model saved to {args.output}")


if __name__ == '__main__':
    main()
