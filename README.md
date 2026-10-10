# R2U-NET Inspection Pro — Hybrid Desktop App + Dashboard

แปลงระบบจาก Web (Hugging Face + Vercel) ให้เป็น **Desktop App ที่ทำงานภายในเครื่องทั้งหมด** (Offline-first)

งานหลัก (กล้อง, AI, บันทึกผล) ไม่ต้องใช้ Internet เลย และถ้ามี Internet + ตั้งค่า `.env` ไว้ ผลการตรวจจะถูก Sync ขึ้น Supabase และแสดงบน Web Dashboard แบบ Realtime

ตรรกะการคำนวณ (`dice_coeff`, `dice_loss`, `combined_loss`, preprocessing, contour, threshold) คัดลอกจากระบบเดิมแบบ 1:1 และมี Unit Test ป้องกันไม่ให้ถูกแก้โดยไม่ตั้งใจ

> วิธีตั้งค่า Supabase / GitHub / Vercel / Release ดูที่ [`CICTCD_SETUP.md`](CICTCD_SETUP.md)

---

## 1) โครงสร้างโปรเจกต์

```text
r2unet_desktop_final/

├── main.py                         ← จุดเริ่มต้นโปรแกรม (รันไฟล์นี้)
├── requirements.txt                ← Library ที่ใช้รันโปรแกรม (ล็อกเวอร์ชัน)
├── requirements-dev.txt            ← + pytest, pyinstaller (สำหรับ test / build)
├── .env.example                    ← Template ของ .env (Supabase keys)

├── models/                         ← เอาไฟล์โมเดล .h5 มาวางตรงนี้
│   ├── defect_model.h5
│   └── r2unet__model_underbody_screw.h5

├── data/
│   └── inspections.db              ← SQLite (สร้างอัตโนมัติเมื่อรันครั้งแรก)

├── core/
│   ├── losses.py                   ← dice_coeff / dice_loss / combined_loss (ห้ามแก้)
│   ├── model_manager.py            ← โหลด/เก็บโมเดลทั้ง 2 ตัวในหน่วยความจำ
│   ├── inference.py                ← Logic การ Predict (คัดลอกจาก Flask /predict เดิม)
│   ├── model_load_worker.py        ← Thread โหลดโมเดลตอนเปิดโปรแกรม
│   ├── batch_worker.py             ← Thread ประมวลผลรูปภาพหลายไฟล์
│   └── cloud_sync.py               ← Thread Sync ผลขึ้น Supabase (offline-first)

├── camera/
│   └── camera_worker.py            ← Thread อ่านภาพจากกล้อง/วิดีโอ + เรียก Inference

├── database/
│   └── db_manager.py               ← SQLite: บันทึกประวัติ / Export CSV

├── ui/
│   ├── main_window.py              ← หน้าตาโปรแกรมหลัก (PySide6)
│   └── utils.py                    ← แปลงภาพ OpenCV → Qt

├── tests/                          ← Unit tests (รันใน CI ทุกครั้งที่ push)
├── training/                       ← CT: R2U-Net, retrain.py (เทรน) + evaluate.py (gate)
├── dashboard/                      ← Next.js Web Dashboard (deploy ด้วย Vercel)
├── supabase/
│   ├── schema.sql                  ← Schema สำหรับ Project ใหม่
│   └── migrations/                 ← SQL สำหรับอัปเดต Project ที่สร้างไปแล้ว
└── .github/workflows/
    ├── ci.yml                      ← CI: test desktop app
    ├── dashboard-ci.yml            ← CI: build dashboard
    ├── build-release.yml           ← CD: build .exe เมื่อ push tag v*.*.*
    └── retrain.yml                 ← CT: retrain + evaluate (กดรันเอง)
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

# 4. (ไม่บังคับ) ถ้าจะรัน test หรือ build .exe
pip install -r requirements-dev.txt
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
> `requirements.txt` ล็อก `tensorflow==2.21.0` (Keras 3) ไว้แล้ว หากยังพบ Error ดังกล่าว แปลว่า venv ยังใช้ TensorFlow รุ่นเก่าอยู่ ให้รัน:
>
> ```bash
> pip install -r requirements.txt
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
Models ready
```

### ฟังก์ชันหลักที่มีอยู่ในโปรแกรม

ฟังก์ชันทั้งหมดตรงตามโค้ด Web เดิมที่ให้ไว้:

* เลือกโมเดล (Pipe Staple / Underbody Screw)
* ตั้งค่า Pixel Threshold และ Confidence (ปรับระหว่างที่ AI ทำงานอยู่ได้ทันที)
* เปิดกล้อง (เลือกกล้องได้หากมีมากกว่า 1 ตัว)
* เปิดไฟล์วิดีโอ
* กด **Run AI Analysis** เพื่อวิเคราะห์แบบ Real-time
* แสดงกรอบ **MISSING** และสถานะ **GOOD / MISSING**
* อัปโหลดรูปภาพหลายไฟล์พร้อมกัน (Batch)
* แสดงภาพต้นฉบับและผลลัพธ์คู่กัน
* บันทึกผลการตรวจสอบลง SQLite โดยอัตโนมัติ
  * กล้อง/วิดีโอ: บันทึกเฉพาะ `MISSING` — ทันทีที่เปลี่ยนจาก GOOD เป็น MISSING และถ้ายังเจออยู่ บันทึกซ้ำไม่เกินทุก 5 วินาที (`LIVE_LOG_COOLDOWN_SEC` ใน `ui/main_window.py`)
  * Batch Images: บันทึกทุกภาพ (ทั้ง GOOD และ MISSING)
* ดูประวัติการตรวจสอบทั้งหมดในแท็บ **Inspection History** (อัปเดตอัตโนมัติ)
* ปุ่ม **Export CSV Report** ในแท็บ Inspection History
* ปุ่ม **Clear History** ในแท็บ Inspection History — ลบประวัติทั้งหมดที่เก็บในเครื่องนี้ (มีหน้าต่างให้ยืนยันก่อน และเตือนถ้ายังมีข้อมูลที่ยังไม่ได้ Sync) ข้อมูลที่ Sync ขึ้น Supabase ไปแล้วจะไม่ถูกลบ
* Sync ผลขึ้น Supabase อัตโนมัติเมื่อมี Internet (ถ้าตั้งค่า `.env` ไว้) — ไม่มีเน็ตก็ทำงานได้ปกติ ข้อมูลจะรอ Sync ทีหลัง

### รัน Unit Test

```bash
pytest tests/ -v
```

### ประสิทธิภาพของโมเดล Pipe Staple (`models/defect_model.h5`)

R2U-Net ขนาด input 128x128 (2.46 ล้านพารามิเตอร์) เทรนด้วย AutoVI `pipe_staple` แบ่งข้อมูลแบบไม่ซ้ำกัน
ผลบน **test set ที่โมเดลไม่เคยเห็น** (188 good + 24 missing) วัดด้วยโค้ดของแอปเอง ค่าตั้งต้น Confidence 0.35 / Pixel Threshold 500:

| ตัววัด | ผล |
|---|---|
| Recall (จับชิ้นที่หายได้) | 0.958 (23/24) |
| Specificity (ของดีผ่าน) | 1.000 (188/188) |
| Precision | 1.000 |
| Dice เฉลี่ย (ภาพที่มี defect) | 0.876 |
| IoU เฉลี่ย (ภาพที่มี defect) | 0.808 |
| ความเร็ว (CPU, รวม preprocessing) | ~31 ms/ภาพ |

ภาพที่พลาด 1 ภาพ (`test/missing/0012.png`) มีลักษณะต่างจากภาพอื่นทั้งหมดในชุดข้อมูล (ชิ้นส่วนสีขาวสว่างทับตำแหน่ง defect) และไม่มีภาพแบบนี้ในชุดเทรน
เทรนซ้ำได้ด้วย `training/retrain.py` หรือ CT workflow (ดู `training/README.md`)

---

## 5) การ Build เป็นไฟล์ `.exe` (สำหรับนำไปติดตั้งเครื่องหน้างาน)

> วิธีที่แนะนำ: ให้ GitHub Actions build ให้อัตโนมัติด้วยการ push tag (ดู `CICTCD_SETUP.md` Part 5) ส่วนด้านล่างคือวิธี build เองในเครื่อง

ติดตั้ง PyInstaller:

```bash
pip install -r requirements-dev.txt
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

ถ้าต้องการ Cloud sync ให้คัดลอกไฟล์ `.env` ไปวางไว้ข้าง ๆ `R2UNET_Inspection_Pro.exe` ด้วย (ฐานข้อมูล `data/inspections.db` จะถูกสร้างไว้ข้าง `.exe` เช่นกัน)

สามารถคัดลอกทั้งโฟลเดอร์นี้ไปติดตั้งบนคอมพิวเตอร์หน้างานได้เลย

โดย **ไม่จำเป็นต้องติดตั้ง Python เพิ่ม** และไม่ต้องเชื่อมต่อ Internet สำหรับการทำงานหลัก เพราะ Library และโมเดลที่จำเป็นถูกรวมอยู่ในโฟลเดอร์แล้ว

> **ข้อควรระวัง:** ไฟล์โมเดล `.h5` มีขนาดใหญ่ ดังนั้นขนาดไฟล์ติดตั้งสุดท้ายจะใหญ่ตามไปด้วย ซึ่งเป็นเรื่องปกติสำหรับการรวม TensorFlow และโมเดลไว้ในตัวโปรแกรม

---

## 6) ข้อกำกับของงาน

* ตรรกะการคำนวณทั้งหมด ได้แก่:

  * `dice_coeff`
  * `dice_loss`
  * `combined_loss`
  * ขั้นตอน Preprocessing
  * Resize `128x128`
  * การ Threshold ด้วย Confidence
  * การหา Contour
  * การวาดกรอบ `MISSING`

  โดยอยู่ในไฟล์:

  ```text
  core/losses.py
  core/inference.py
  ```

* สถาปัตยกรรมถูกแยกเป็น **UI / Camera / AI / Database / Controller** ตามที่ร้องขอ

* ระบบทำงานแบบ **Hybrid Desktop App + Dashboard**

* งานหลักไม่จำเป็นต้องพึ่งพา Internet (Internet ใช้เฉพาะ Cloud sync)
