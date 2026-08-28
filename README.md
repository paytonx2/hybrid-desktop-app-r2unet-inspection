# R2U-NET Inspection Pro — Desktop (Offline)

แปลงระบบจาก Web (HuggingFace + Vercel) ใหเ้ป็น **Desktop App ทที่ ำ งานในเครอื่งทงั้หมด**
ไมต่ อ้ งใช ้internet หรอื server ภายนอกในการทำ งานหลกัอกีตอ่ ไป
ตรรกะการคำนวณ (dice_coeff, dice_loss, combined_loss, preprocessing, contour, threshold)
**คดั ลอกมาจาก backend เดมิ แบบ 1:1 ไมม่ กีารแกไ้ข**

---

## 1) โครงสรา้งโปรเจกต์

```
r2unet_desktop/
├── main.py                  ← จุดเรมิ่ตน้ โปรแกรม (รันไฟลน์ ี้)
├── requirements.txt
├── models/                  ← ★ เอาไฟลโ์มเดล .h5 มาวางตรงนี้ ★
│   ├── defect_model.h5
│   └── r2unet__model_underbody_screw.h5
├── data/
│   └── inspections.db       ← SQLite (สรา้งอตัโนมตั เิมอื่ รันครัง้แรก)
├── core/
│   ├── losses.py            ← dice_coeff / dice_loss / combined_loss (หา้มแก)้
│   ├── model_manager.py     ← โหลด/เกบ็ โมเดลทงั้ 2 ตวัในหน่วยความจำ
│   ├── inference.py         ← logic การ predict (คดัลอกจาก Flask /predict เดมิ )
│   ├── model_load_worker.py ← thread โหลดโมเดลตอนเปิดโปรแกรม
│   └── batch_worker.py      ← thread ประมวลผลรปูภาพหลายไฟล์
├── camera/
│   └── camera_worker.py     ← thread อา่ นภาพจากกลอ้ ง/วดิโีอ + เรยีก inference
├── database/
│   └── db_manager.py        ← SQLite: บนั ทกึประวตั /ิ export CSV
└── ui/
    ├── main_window.py       ← หนา้ตาโปรแกรมหลกั (PySide6)
    └── utils.py              ← แปลงภาพ OpenCV → Qt
```

สถาปตัยกรรมแยกเป็นสว่ น ๆ (UI / Camera / AI / Database / Controller) ตามทตี่ อ้ งการ
ทำ ใหอ้ นาคตถา้อยากเพมิ่โมเดลใหม่, เปลยี่ น UI, หรอืเปลยี่ นฐานขอ้มลู ทำ ไดโ้ดยไมก่ ระทบสว่ นอนื่

---

## 2) สงิ่ ทตี่อ้งตดิตัง้ (ทำ ครัง้เดยีว)

เปิด VS Code → เปิด Terminal (Ctrl+`) แลว้ รันตามลำดบั:

```bash
# 1. แนะนำใหส้ รา้ง virtual environment กอ่ น (กนัไลบรารชีนกบัโปรเจกตอ์ นื่)
python -m venv venv

# 2. เปิดใชง้าน venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. ตดิตงั้ไลบรารที งั้หมด
pip install -r requirements.txt
```

> หมายเหตุ: ถา้เครอื่งมกีารด์ จอ NVIDIA และตอ้งการใหร้ นัเร็วขนึ้ดว้ ย GPU
> ตอ้งตดิตงั้ `tensorflow` เวอรช์ นั ทรี่ องรับ CUDA/cuDNN แยกตา่ งหาก (ไมบ่ งัคบั เครอื่งไมม่ กีาร์
> จอกร็ นัไดป้ กตดิว้ ย CPU เพยีงชา้กวา่)
>
> **สำคญั:** ไฟล ์`.h5` ทเี่ทรนดว้ ย Keras รนุ่ ใหม ่(Keras 3) จะโหลดไมไ่ดถ้ า้ tensorflow เกา่ เกนิ ไป
> (จะขนึ้ error ประมาณ `Unrecognized keyword arguments: ['batch_shape']`) — `requirements.txt`
> นบี้ งัคบั `tensorflow>=2.16` ไวแ้ ลว้ เพอื่ แกป้ ัญหานี้ ถา้ยงัเจอ error นี้อยใู่หร้ นั
> `pip install --upgrade tensorflow` อกีครัง้

VS Code Extension ทแี่นะนำ: **Python** (Microsoft) และ **Pylance**

---

## 3) นำ โมเดลของคณุ มาวาง

คดัลอกไฟล์
```
defect_model.h5
r2unet__model_underbody_screw.h5
```
ไปวางไวใ้นโฟลเดอร ์`models/` (ชอื่ ไฟลต์ อ้งตรงเป๊ะตามนี้ — ถา้ชอื่ ไมต่ รง ใหแ้กช้อื่ ไฟล ์
หรอืแกพ้าธใ์นฟังกช์นั `default_paths()` ในไฟล ์`core/model_manager.py`)

---

## 4) วธิรีนัโปรแกรม (ตอนพัฒนา)

```bash
python main.py
```

โปรแกรมจะขนึ้หนา้ตา่ ง Desktop ทนั ท ีและเรมิ่โหลดโมเดลใน background (ดสูถานะไดท้ มี่ มุ บนซา้ ยของ
Sidebar และใน System Terminal) พอโหลดเสร็จจะขนึ้ "✅ โมเดลพรอ้ มใชง้าน"

ฟังกช์นั หลกัทมี่ อียใู่นโปรแกรมนี้(ตรงตามโค็ดเว็บทใี่หไ้ปทกุ ประการ):

- เลอืกโมเดล (Pipe Staple / Underbody Screw)
- ตงั้คา่ Pixel Threshold และ Confidence
- เปิดกลอ้ ง (เลอืกกลอ้ งไดถ้ า้มมีากกวา่ 1 ตวั) หรอืเปิดไฟลว์ดิโีอ
- กด Run AI Analysis เพอื่ วเิคราะหแ์บบ real-time พรอ้มกรอบ "MISSING" และสถานะ GOOD/MISSING
- อพัโหลดรปูภาพหลายไฟลพ์รอ้มกนั (Batch) พรอ้มแสดงภาพตน้ ฉบบั /ผลลพัธค์ กู่นั
- บนั ทกึทกุ ผลตรวจสอบลง SQLite อตัโนมตั ิ(เมอื่ พบ MISSING)
- ดปูระวตั กิารตรวจสอบทงั้หมดในแทป็ "ประวตั กิารตรวจสอบ"
- Export CSV Report

---

## 5) การ Build เป็นไฟล ์.exe (สำหรบันำ ไปตดิตงั้เครอื่ งหนา้งาน)

ตดิตงั้ PyInstaller:
```bash
pip install pyinstaller
```

จากนัน้ รนัคำสงั่ (รนัในโฟลเดอรโ์ปรเจกต ์เดยีวกบั main.py):

```bash
pyinstaller --noconfirm --onedir --windowed ^
  --name "R2UNET_Inspection_Pro" ^
  --add-data "models;models" ^
  main.py
```

(บน macOS/Linux ใหเ้ปลยี่ น `;` เป็น `:` ในพารามเิตอร ์`--add-data` และเปลยี่ น `^` เป็น `\`)

ผลลพัธจ์ ะอยใู่ น `dist/R2UNET_Inspection_Pro/` — คดัลอกทงั้โฟลเดอรน์ ไี้ปตดิตงั้บนเครอื่งคอมพวิเตอร์
หนา้งานไดเ้ลย โดยไมต่ อ้งตดิตงั้ Python หรอืตอ่ internet เพราะทกุอยา่ งรวมอยใู่นโฟลเดอรน์ ั้นแลว้

> ขอ้ควรระวงั: ไฟลโ์มเดล .h5 มขี นาดใหญ่ ขนาดไฟลต์ ดิตงั้สดุ ทา้ยจะใหญต่ ามไปดว้ ย (ปกตขิอง
> การรวม TensorFlow + โมเดลไวใ้นตวั)

---

## 6) ขอ้ทกี่ ำ กบัไวต้ ามคำ ขอ

- ตรรกะคำนวณทงั้หมด (`dice_coeff`, `dice_loss`, `combined_loss`, ขนั้ตอน preprocessing/resize
  128x128, การ threshold ดว้ ย confidence, การหา contour และวาดกรอบ MISSING) **คดัลอกมาจาก
  backend เดมิ แบบคำตอ่ คำ ไมม่ กีารแกไ้ข** อยใู่นไฟล ์`core/losses.py` และ `core/inference.py`
- สถาปตัยกรรมแยกเป็น UI / Camera / AI / Database / Controller ตามทรี่ อ้ งขอ
- ทำ งานแบบ local ทงั้หมด ไมต่ อ้ งพงึ่ Hugging Face API หรอื internet อกีตอ่ ไป
