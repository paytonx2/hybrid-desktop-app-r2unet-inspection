"""
Custom loss / metric functions used by the R2U-NET models.

!! หา้มแกไ้ขคา่ /สตู รในไฟลน์ ี้เด็ดขาด !!
คดั ลอกมาจาก backend เดมิ (Flask) แบบ 1:1 เพอื่ ใหผ้ ลลพัธก์ ารทำ นายเหมอื นเดมิ ทกุ ประการ
"""

import tensorflow as tf
from tensorflow.keras import backend as K


def dice_coeff(y_true, y_pred, smooth=1e-6):
    y_true_f = K.flatten(y_true)
    y_pred_f = K.flatten(y_pred)
    intersection = K.sum(y_true_f * y_pred_f)
    return (2. * intersection + smooth) / (K.sum(y_true_f) + K.sum(y_pred_f) + smooth)


def dice_loss(y_true, y_pred):
    return 1 - dice_coeff(y_true, y_pred)


def combined_loss(y_true, y_pred):
    return 0.5 * tf.keras.losses.binary_crossentropy(y_true, y_pred) + 0.5 * dice_loss(y_true, y_pred)


CUSTOM_OBJECTS = {
    'dice_coeff': dice_coeff,
    'dice_loss': dice_loss,
    'combined_loss': combined_loss,
}
