# R2U-NET Inspection Pro — Desktop (Offline)

แปลงระบบจาก Web (Hugging Face + Vercel) ให้เป็น **Desktop App ที่ทำงานภายในเครื่องทั้งหมด**

ไม่ต้องใช้งาน Internet หรือ Server ภายนอกในการทำงานหลักอีกต่อไป

ตรรกะการคำนวณ (`dice_coeff`, `dice_loss`, `combined_loss`, preprocessing, contour, threshold)

**คัดลอกมาจาก Backend เดิมแบบ 1:1 ไม่มีการแก้ไข**

---

## 1) โครงสร้างโปรเจกต์

```text
r2unet_desktop/

├── main.py                         ← จุดเริ่มต้นโปรแกรม (รันไฟล์นี้)
├── requirements.txt

├── models/                         ← ★ เอาไฟล์โมเดล .h5 มาวางตรงนี้ ★
│   ├── defect_model.h5
│   └── r2unet__model_underbody_screw.h5

├── data/
│   └── inspections.db              ← SQLite (สร้างอัตโนมัติเมื่อรันครั้งแรก)

├── core/
│   ├── losses.py                   ← dice_coeff / dice_loss / combined_loss (ห้ามแก้)
│   ├── model_manager.py            ← โหลด/เก็บโมเดลทั้ง 2 ตัวในหน่วยความจำ
│   ├── inference.py                ← Logic การ Predict (คัดลอกจาก Flask /predict เดิม)
│   ├── model_load_worker.py        ← Thread โหลดโมเดลตอนเปิดโปรแกรม
│   └── batch_worker.py             ← Thread ประมวลผลรูปภาพหลายไฟล์

├── camera/
│   └── camera_worker.py            ← Thread อ่านภาพจากกล้อง/วิดีโอ + เรียก Inference

├── database/
│   └── db_manager.py               ← SQLite: บันทึกประวัติ / Export CSV

└── ui/
    ├── main_window.py              ← หน้าตาโปรแกรมหลัก (PySide6)
    └── utils.py                    ← แปลงภาพ OpenCV → Qt
```

สถาปัตยกรรมถูกแยกเป็นส่วน ๆ ได้แก่ **UI / Camera / AI / Database / Controller** ตามที่ต้องการ

ทำให้ในอนาคต หากต้องการเพิ่มโมเดลใหม่ เปลี่ยน UI หรือเปลี่ยนฐานข้อมูล ก็สามารถทำได้โดยไม่กระทบกับส่วนอื่น

---

## 2) สิ่งที่ต้องติดตั้ง (ทำครั้งเดียว)

เปิด VS Code → เปิด Terminal (`Ctrl + ``) แล้วรันตามลำดับ:

```bash
# 1. แนะนำให้สร้าง Virtual Environment ก่อน
#    เพื่อป้องกัน Library ชนกับโปรเจกต์อื่น
python -m venv venv

# 2. เปิดใช้งาน venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. ติดตั้ง Library ทั้งหมด
pip install -r requirements.txt
```

> **หมายเหตุ:** หากเครื่องมีการ์ดจอ NVIDIA และต้องการให้รันเร็วขึ้นด้วย GPU
>
> ต้องติดตั้ง `tensorflow` เวอร์ชันที่รองรับ CUDA/cuDNN แยกต่างหาก (ไม่บังคับ เครื่องที่ไม่มีการ์ดจอก็รันได้ตามปกติด้วย CPU เพียงแต่จะช้ากว่า)

> **สำคัญ:** ไฟล์ `.h5` ที่เทรนด้วย Keras รุ่นใหม่ (Keras 3) อาจโหลดไม่ได้หากใช้ TensorFlow รุ่นเก่าเกินไป
>
> อาจพบ Error ประมาณ:
>
> `Unrecognized keyword arguments: ['batch_shape']`
>
> `requirements.txt` นี้กำหนด `tensorflow>=2.16` ไว้แล้วเพื่อช่วยแก้ปัญหานี้ หากยังพบ Error ดังกล่าว ให้รัน:
>
> ```bash
> pip install --upgrade tensorflow
> ```

VS Code Extension ที่แนะนำ:

* **Python** (Microsoft)
* **Pylance**

---

## 3) นำโมเดลของคุณมาวาง

คัดลอกไฟล์:

```text
defect_model.h5
r2unet__model_underbody_screw.h5
```

ไปวางไว้ในโฟลเดอร์:

```text
models/
```

**ชื่อไฟล์ต้องตรงตามนี้ทุกตัวอักษร**

หากชื่อไม่ตรง สามารถแก้ชื่อไฟล์ หรือแก้ Path ในฟังก์ชัน `default_paths()` ภายในไฟล์:

```text
core/model_manager.py
```

---

## 4) วิธีรันโปรแกรม (ตอนพัฒนา)

รันคำสั่ง:

```bash
python main.py
```

โปรแกรมจะเปิดหน้าต่าง Desktop ทันที และเริ่มโหลดโมเดลใน Background

สามารถดูสถานะได้ที่:

* มุมบนซ้ายของ Sidebar
* System Terminal

เมื่อโหลดโมเดลเสร็จ จะขึ้นข้อความ:

```text
✅ โมเดลพร้อมใช้งาน
```

### ฟังก์ชันหลักที่มีอยู่ในโปรแกรม

ฟังก์ชันทั้งหมดตรงตามโค้ด Web เดิมที่ให้ไว้:

* เลือกโมเดล (Pipe Staple / Underbody Screw)
* ตั้งค่า Pixel Threshold และ Confidence
* เปิดกล้อง (เลือกกล้องได้หากมีมากกว่า 1 ตัว)
* เปิดไฟล์วิดีโอ
* กด **Run AI Analysis** เพื่อวิเคราะห์แบบ Real-time
* แสดงกรอบ **MISSING** และสถานะ **GOOD / MISSING**
* อัปโหลดรูปภาพหลายไฟล์พร้อมกัน (Batch)
* แสดงภาพต้นฉบับและผลลัพธ์คู่กัน
* บันทึกผลการตรวจสอบลง SQLite โดยอัตโนมัติ (เมื่อพบ `MISSING`)
* ดูประวัติการตรวจสอบทั้งหมดในแท็บ **ประวัติการตรวจสอบ**
* Export CSV Report

---

## 5) การ Build เป็นไฟล์ `.exe` (สำหรับนำไปติดตั้งเครื่องหน้างาน)

ติดตั้ง PyInstaller:

```bash
pip install pyinstaller
```

จากนั้นรันคำสั่งต่อไปนี้ในโฟลเดอร์โปรเจกต์เดียวกับ `main.py`:

### Windows

```bash
pyinstaller --noconfirm --onedir --windowed ^
  --name "R2UNET_Inspection_Pro" ^
  --add-data "models;models" ^
  main.py
```

### macOS / Linux

ให้เปลี่ยน `;` เป็น `:` ในพารามิเตอร์ `--add-data` และเปลี่ยน `^` เป็น `\`

ตัวอย่าง:

```bash
pyinstaller --noconfirm --onedir --windowed \
  --name "R2UNET_Inspection_Pro" \
  --add-data "models:models" \
  main.py
```

ผลลัพธ์จะอยู่ที่:

```text
dist/R2UNET_Inspection_Pro/
```

สามารถคัดลอกทั้งโฟลเดอร์นี้ไปติดตั้งบนคอมพิวเตอร์หน้างานได้เลย

โดย **ไม่จำเป็นต้องติดตั้ง Python เพิ่ม** และไม่ต้องเชื่อมต่อ Internet สำหรับการทำงานหลัก เพราะ Library และโมเดลที่จำเป็นถูกรวมอยู่ในโฟลเดอร์แล้ว

> **ข้อควรระวัง:** ไฟล์โมเดล `.h5` มีขนาดใหญ่ ดังนั้นขนาดไฟล์ติดตั้งสุดท้ายจะใหญ่ตามไปด้วย ซึ่งเป็นเรื่องปกติสำหรับการรวม TensorFlow และโมเดลไว้ในตัวโปรแกรม

---

## 6) ข้อกำกับตามคำขอ

* ตรรกะการคำนวณทั้งหมด ได้แก่:

  * `dice_coeff`
  * `dice_loss`
  * `combined_loss`
  * ขั้นตอน Preprocessing
  * Resize `128x128`
  * การ Threshold ด้วย Confidence
  * การหา Contour
  * การวาดกรอบ `MISSING`

  **คัดลอกมาจาก Backend เดิมแบบคำต่อคำ ไม่มีการแก้ไข**

  โดยอยู่ในไฟล์:

  ```text
  core/losses.py
  core/inference.py
  ```

* สถาปัตยกรรมถูกแยกเป็น **UI / Camera / AI / Database / Controller** ตามที่ร้องขอ

* ระบบทำงานแบบ **Local ทั้งหมด**

* ไม่ต้องพึ่งพา **Hugging Face API** หรือ Internet ในการทำงานหลักอีกต่อไป
