"""
ตรรกะการ inference / preprocessing / postprocessing
คดั ลอกมาจาก endpoint /predict ของ backend เดมิ (Flask) แบบ 1:1
เปลยี่ นแคว่ธิรี บั -สง่ ขอ้มลู (ไมม่ ี HTTP / base64 อกี ตอ่ ไป เพราะรันในเครอื่งโดยตรง)
"""

import cv2
import numpy as np


def run_inference(img_bgr, model, conf_threshold=0.35, px_threshold=500):
    """
    img_bgr: numpy array (H, W, 3) รปูแบบ BGR (เชน่ จาก cv2.imread หรอื cv2.VideoCapture)
    model: โมเดล keras ทโี่ หลดแลว้ (จาก ModelManager.get_model)
    คนื คา่ dict: status, pixel_count, result_bgr (ภาพผลลพัธพ์รอ้ มกรอบ/overlay, BGR)
    """
    h_orig, w_orig = img_bgr.shape[:2]

    # ===== Preprocessing (เหมอื นเดมิ ) =====
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_input = cv2.resize(img_rgb, (128, 128))
    img_input = img_input.astype('float32') / 255.0
    img_input = np.expand_dims(img_input, axis=0)

    # ===== Inference (เหมอื นเดมิ ) =====
    pred_mask = model.predict(img_input, verbose=0)[0]
    mask_binary = (pred_mask > conf_threshold).astype(np.uint8)

    # Resize back to original
    mask_full = cv2.resize(mask_binary, (w_orig, h_orig), interpolation=cv2.INTER_NEAREST)
    pixel_count = int(np.sum(mask_full))

    # ===== Visualization (เหมอื นเดมิ ) =====
    result_view = img_rgb.copy()
    result_view[mask_full == 1] = [255, 0, 0]  # Red overlay
    result_view = cv2.addWeighted(result_view, 0.5, img_rgb, 0.5, 0)

    contours, _ = cv2.findContours(
        mask_full.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    for cnt in contours:
        if cv2.contourArea(cnt) > px_threshold:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(result_view, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                result_view, "MISSING", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
            )

    status = "MISSING" if pixel_count >= px_threshold else "GOOD"
    result_bgr = cv2.cvtColor(result_view, cv2.COLOR_RGB2BGR)

    return {
        'status': status,
        'pixel_count': pixel_count,
        'result_bgr': result_bgr,
    }
