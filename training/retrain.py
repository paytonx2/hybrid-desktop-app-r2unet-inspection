"""
Skeleton for the "Continuous Training" step of the pipeline.

This intentionally does NOT contain a real R2U-Net architecture or a real
dataset loader, because those depend on how you originally trained
defect_model.h5 / r2unet__model_underbody_screw.h5 (which wasn't provided).
Fill in the two TODO sections below with your actual training code, then
this script slots directly into the retrain.yml GitHub Actions workflow.

The one part that MUST stay untouched is the loss import below — training
and inference have to use the exact same math or the model's behavior will
silently diverge from what the desktop app expects.

Usage:
    python training/retrain.py --train-dir training/data/train \
                                --output training/output/candidate_model.h5
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.losses import combined_loss, dice_coeff  # noqa: E402  (kept identical to inference)


def build_model():
    """
    TODO: replace this with your actual R2U-Net architecture.
    This placeholder is a tiny U-Net-shaped model just so the
    pipeline is runnable end-to-end before you plug in the real one.
    """
    import tensorflow as tf
    from tensorflow.keras import layers

    inputs = tf.keras.Input(shape=(128, 128, 3))
    x = layers.Conv2D(16, 3, activation='relu', padding='same')(inputs)
    x = layers.MaxPooling2D()(x)
    x = layers.Conv2D(32, 3, activation='relu', padding='same')(x)
    x = layers.UpSampling2D()(x)
    outputs = layers.Conv2D(1, 1, activation='sigmoid', padding='same')(x)
    return tf.keras.Model(inputs, outputs)


def load_training_data(train_dir):
    """
    TODO: replace with your real dataset loader.
    Expected layout (same convention as training/evaluate.py):
        train_dir/images/*.png
        train_dir/masks/*.png
    """
    from training.evaluate import load_validation_set  # reuses the same loader shape
    return load_validation_set(train_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-dir', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--epochs', type=int, default=5)
    args = parser.parse_args()

    import tensorflow as tf

    x_train, y_train = load_training_data(args.train_dir)
    print(f"Training set: {len(x_train)} image/mask pairs")

    model = build_model()
    model.compile(optimizer='adam', loss=combined_loss, metrics=[dice_coeff])
    model.fit(x_train, y_train, epochs=args.epochs, batch_size=8)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    model.save(args.output)
    print(f"Candidate model saved to {args.output}")


if __name__ == '__main__':
    main()
