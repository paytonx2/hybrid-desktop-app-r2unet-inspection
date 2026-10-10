"""
R2U-Net (Alom et al., 2018) — same architecture as the training notebook in
D:\\MODEL R2U-NET that produced models/defect_model.h5.

- Recurrent block: one Conv3x3 whose weights are shared across all t+1 time
  steps (that is what makes it recurrent); each step receives input + previous
  output. BatchNorm is separate per step: sharing it made the inference-time
  statistics wrong (val_loss blew up in early tests).
- RRCNN block: Conv1x1 to set channels -> 2 recurrent blocks -> residual add.
- 5-level encoder, decoder with up-conv (UpSampling + Conv3x3 + BN + ReLU).
"""
from tensorflow import keras
from tensorflow.keras import layers


def recurrent_block(x, filters, t):
    conv = layers.Conv2D(filters, 3, padding='same')
    x1 = layers.ReLU()(layers.BatchNormalization(momentum=0.9)(conv(x)))
    for _ in range(t):
        x1 = layers.ReLU()(layers.BatchNormalization(momentum=0.9)(conv(layers.Add()([x, x1]))))
    return x1


def rrcnn_block(x, filters, t):
    x = layers.Conv2D(filters, 1, padding='same')(x)
    x1 = recurrent_block(x, filters, t)
    x1 = recurrent_block(x1, filters, t)
    return layers.Add()([x, x1])


def up_conv(x, filters):
    x = layers.UpSampling2D(2)(x)
    x = layers.Conv2D(filters, 3, padding='same')(x)
    x = layers.BatchNormalization()(x)
    return layers.ReLU()(x)


def build_r2unet(input_shape=(128, 128, 3), base_filters=16, t=2):
    f = [base_filters * 2 ** i for i in range(5)]
    inputs = keras.Input(input_shape)

    e1 = rrcnn_block(inputs, f[0], t)
    e2 = rrcnn_block(layers.MaxPooling2D()(e1), f[1], t)
    e3 = rrcnn_block(layers.MaxPooling2D()(e2), f[2], t)
    e4 = rrcnn_block(layers.MaxPooling2D()(e3), f[3], t)
    e5 = rrcnn_block(layers.MaxPooling2D()(e4), f[4], t)

    d4 = rrcnn_block(layers.Concatenate()([e4, up_conv(e5, f[3])]), f[3], t)
    d3 = rrcnn_block(layers.Concatenate()([e3, up_conv(d4, f[2])]), f[2], t)
    d2 = rrcnn_block(layers.Concatenate()([e2, up_conv(d3, f[1])]), f[1], t)
    d1 = rrcnn_block(layers.Concatenate()([e1, up_conv(d2, f[0])]), f[0], t)

    outputs = layers.Conv2D(1, 1, activation='sigmoid', name='mask')(d1)
    return keras.Model(inputs, outputs, name='R2U_Net')
