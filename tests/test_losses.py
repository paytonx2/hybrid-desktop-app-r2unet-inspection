"""
These tests protect the one rule that must never break: the dice/combined
loss math must stay byte-for-byte identical to what the models were
trained with. If someone "helpfully" simplifies this file later, CI fails.
"""
import numpy as np
import tensorflow as tf

from core.losses import dice_coeff, dice_loss, combined_loss


def test_dice_coeff_identical_masks_is_one():
    mask = tf.constant(np.ones((1, 8, 8, 1), dtype='float32'))
    score = dice_coeff(mask, mask).numpy()
    assert abs(score - 1.0) < 1e-4


def test_dice_coeff_disjoint_masks_is_near_zero():
    a = tf.constant(np.array([[1, 1, 0, 0]], dtype='float32'))
    b = tf.constant(np.array([[0, 0, 1, 1]], dtype='float32'))
    score = dice_coeff(a, b).numpy()
    assert score < 0.05


def test_dice_loss_is_one_minus_dice_coeff():
    a = tf.constant(np.array([[1, 1, 0, 0]], dtype='float32'))
    b = tf.constant(np.array([[1, 0, 0, 0]], dtype='float32'))
    assert abs(dice_loss(a, b).numpy() - (1 - dice_coeff(a, b).numpy())) < 1e-5


def test_dice_coeff_golden_value():
    # intersection = 1, sum(a) = 2, sum(b) = 1  ->  (2*1 + 1e-6) / (3 + 1e-6)
    a = tf.constant(np.array([[1, 1, 0, 0]], dtype='float32'))
    b = tf.constant(np.array([[1, 0, 0, 0]], dtype='float32'))
    assert abs(dice_coeff(a, b).numpy() - (2.0 + 1e-6) / (3.0 + 1e-6)) < 1e-6


def test_combined_loss_golden_value():
    # 0.5 * BCE + 0.5 * dice_loss, with BCE computed by hand
    y_true = tf.constant(np.array([[1.0, 0.0]], dtype='float32'))
    y_pred = tf.constant(np.array([[0.8, 0.4]], dtype='float32'))
    bce = -(np.log(0.8) + np.log(1 - 0.4)) / 2
    dice = (2 * 0.8 + 1e-6) / (1.0 + 1.2 + 1e-6)
    expected = 0.5 * bce + 0.5 * (1 - dice)
    assert abs(float(combined_loss(y_true, y_pred).numpy()[0]) - expected) < 1e-4


def test_combined_loss_is_finite():
    y_true = tf.constant(np.random.randint(0, 2, size=(2, 16, 16, 1)).astype('float32'))
    y_pred = tf.constant(np.random.rand(2, 16, 16, 1).astype('float32'))
    loss = combined_loss(y_true, y_pred).numpy()
    assert np.all(np.isfinite(loss))
