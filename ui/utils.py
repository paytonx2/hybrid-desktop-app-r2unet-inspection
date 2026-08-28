import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap


def cvimg_to_qpixmap(img_bgr):
    if img_bgr is None:
        return QPixmap()
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = img_rgb.shape
    bytes_per_line = ch * w
    qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


def scale_pixmap_to_label(pixmap, label):
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(
        label.width(), label.height(),
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )
