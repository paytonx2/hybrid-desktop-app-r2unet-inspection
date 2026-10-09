# คู่มือการตั้งค่า CI/CT/CD — ส่วนที่ “คุณเท่านั้น” ที่ทำได้

ทุกอย่างที่เกี่ยวข้องกับโค้ดถูกเขียนไว้เรียบร้อยแล้ว ได้แก่ **โมดูล Sync, Dashboard, Supabase Schema และ GitHub Actions ทั้ง 3 Workflow**

สิ่งที่เหลือคือการสร้างบัญชี, ตั้งค่า Keys และการกดตั้งค่าบางอย่าง ซึ่งส่วนนี้ **ต้องใช้บัญชีของคุณเอง จึงไม่มีใครทำแทนได้**

ให้ทำตาม **ลำดับนี้** ใช้เวลาประมาณ **30–45 นาที**

---

# Part 1 — Supabase (ฐานข้อมูลบน Cloud)

### 1. สร้างบัญชี Supabase

เข้าไปที่ **https://supabase.com** → กด **Start your project** → สมัครสมาชิก

แนะนำให้ Login ด้วย GitHub เพราะเร็วที่สุด

### 2. สร้าง Project ใหม่

กด **New Project**

ตั้งค่าประมาณนี้:

* ชื่อ Project เช่น `r2unet-inspection`
* ตั้งรหัสผ่าน Database และเก็บไว้ในที่ปลอดภัย
* เลือก Region ที่ใกล้กับคุณที่สุด
* กด **Create new project**

ระบบจะใช้เวลาประมาณ **2 นาที** ในการสร้าง Project

### 3. เปิด SQL Editor

เมื่อ Project พร้อมแล้ว ให้ไปที่

**SQL Editor** → **New query**

### 4. สร้าง Database Schema

เปิดไฟล์

`supabase/schema.sql`

จากโปรเจกต์ของคุณ แล้ว:

1. Copy เนื้อหาทั้งหมด
2. นำไปวางใน SQL Editor
3. กด **Run**

ระบบจะสร้างตารางที่จำเป็นให้

### 5. เปิด Realtime

ไปที่

**Database → Replication**

จากนั้นตรวจสอบว่าตาราง

`inspections`

ถูกเปิดใช้งาน **Realtime** อยู่

> ใน Schema มีคำสั่งพยายามเปิด Realtime ให้อัตโนมัติอยู่แล้ว แต่ควรเข้ามาตรวจสอบอีกครั้งว่าเปิดสำเร็จจริง

### 6. เอา API Keys

ไปที่

**Project Settings → API**

คุณจะต้องใช้ข้อมูล 2 อย่างจากหน้านี้:

* **Project URL**
  หน้าตาประมาณ `https://xxxxx.supabase.co`

* **anon public** key
  เป็น String ยาว ๆ ที่อยู่ในส่วน **Project API keys**

เก็บหน้านี้เอาไว้ เพราะคุณจะต้อง Copy ค่า 2 ตัวนี้ไปใช้ในขั้นตอนต่อไป

### 7. (ถ้าเคยรัน `schema.sql` เวอร์ชันเก่าไปแล้ว) รัน Migration

ถ้าสร้างตาราง `inspections` ไปก่อนหน้านี้แล้ว ให้เปิดไฟล์

`supabase/migrations/001_local_id_dedup.sql`

แล้ว Copy ไปรันใน **SQL Editor** อีกครั้ง ไฟล์นี้จะ:

* เพิ่มคอลัมน์ `local_id` + Unique constraint เพื่อ **กันข้อมูลซ้ำ** เวลา Sync ซ้ำ
* (ไม่บังคับ) มีคำสั่งแก้เวลาของข้อมูลเก่าที่เพี้ยนไป 7 ชั่วโมง — ถูก comment ไว้ ถ้าจะใช้ให้ลบ `--` หน้าบรรทัด `update` แล้วรัน **ครั้งเดียวเท่านั้น**

> ถ้ายังไม่รัน Migration แอปยัง Sync ได้ตามปกติ แต่จะขึ้นข้อความใน Log ว่า `duplicate protection is off`

---

# Part 2 — เชื่อม Desktop App เข้ากับ Supabase

### 1. สร้างไฟล์ `.env`

ในโฟลเดอร์โปรเจกต์ ให้ Copy ไฟล์

`.env.example`

แล้วสร้างไฟล์ใหม่ชื่อ

`.env`

โดยให้อยู่ในโฟลเดอร์เดียวกับ `main.py`

### 2. ใส่ข้อมูล Supabase

เปิดไฟล์ `.env` แล้วกรอก:

```env
SUPABASE_URL=<วาง Project URL ของคุณที่นี่>
SUPABASE_ANON_KEY=<วาง anon public key ของคุณที่นี่>
DEVICE_ID=my-laptop
```

ตัวอย่าง:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
DEVICE_ID=demo-pc
```

`DEVICE_ID` เป็นเพียงชื่อที่ใช้ระบุเครื่องเท่านั้น

สามารถตั้งเป็นอะไรก็ได้ เช่น:

* `demo-pc`
* `my-laptop`
* `inspection-pc`

### 3. ตรวจสอบ Dependencies

ตรวจสอบว่า Virtual Environment ของคุณมี Dependencies ใหม่ครบแล้ว โดยรัน:

```bash
pip install -r requirements.txt
```

### 4. เปิด Desktop App

รัน:

```bash
python main.py
```

จากนั้นดูที่ Panel **System Terminal** ใน Sidebar

ควรเห็นข้อความประมาณ:

```text
Cloud sync enabled — syncing in the background
```

จากนั้นลองทำ Inspection จริงสักหนึ่งครั้ง เช่น:

* Upload รูปภาพ
* หรือใช้ Camera

ภายในประมาณ **15 วินาที** ควรเห็นข้อความ:

```text
Synced 1 record(s) to Supabase
```

### 5. ตรวจสอบใน Supabase

กลับไปที่ Supabase แล้วเข้า:

**Table Editor → inspections**

ควรเห็นข้อมูล Inspection ที่เพิ่งส่งจาก Desktop App เข้าไป

> **สำคัญ:** ไฟล์ `.env` ถูกใส่ไว้ใน `.gitignore` อยู่แล้ว
> **ห้าม Commit ไฟล์ `.env` ขึ้น GitHub** เพราะมี Keys ของคุณอยู่

---

# Part 3 — GitHub (สำหรับ CI และ CD)

### 1. สร้าง Repository

สร้าง Repository ใหม่บน GitHub

จะตั้งเป็น:

* Public
* หรือ Private

ก็ได้ทั้งคู่

### 2. Push โปรเจกต์ขึ้น GitHub

> ขั้นนี้ทำไปแล้ว (repo: `paytonx2/hybrid-desktop-app-r2unet-inspection`) — หลังจากนี้แค่ `git add`, `git commit`, `git push` ตามปกติ

เปิด Terminal ในโฟลเดอร์โปรเจกต์ แล้วรัน:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

โดยเปลี่ยน:

```text
<your-username>
```

เป็น Username GitHub ของคุณ

และ:

```text
<your-repo>
```

เป็นชื่อ Repository ของคุณ

### 3. ตรวจสอบ CI

เข้า Repository ของคุณบน GitHub → ไปที่แท็บ

**Actions**

คุณควรเห็น Workflow **CI** ทำงานโดยอัตโนมัติ เพราะ Workflow นี้ทำงานทุกครั้งที่มีการ Push

(ถ้าแก้ไฟล์ในโฟลเดอร์ `dashboard/` จะเห็น Workflow **Dashboard CI** ทำงานแทน)

รอจนกว่าจะขึ้นสีเขียว

ถ้าขึ้นสีแดง ให้กดเข้าไปดูรายละเอียดของ Workflow ได้เลย โดย Log จะบอกว่า Test ตัวไหนมีปัญหา

หลังจากตั้งค่านี้เสร็จแล้ว:

> ทุกครั้งที่คุณ Push หรือสร้าง Pull Request ระบบ CI จะทำงานให้อัตโนมัติ

**ไม่จำเป็นต้องตั้งค่าอะไรเพิ่มเติมสำหรับ CI**

---

# Part 4 — Vercel (Deploy Dashboard และ CD สำหรับ Web)

ส่วนนี้ใช้สำหรับ **Dashboard**

### 1. สมัคร Vercel

เข้าไปที่ **https://vercel.com**

สมัครสมาชิกด้วย GitHub Account

### 2. สร้าง Project

กด:

**Add New... → Project**

จากนั้นเลือก GitHub Repository ที่คุณเพิ่ง Push ขึ้นไป

### 3. ตั้ง Root Directory

Vercel จะถามหา **Root Directory**

ให้ตั้งเป็น:

```text
dashboard
```

> **สำคัญมาก** เพราะ Next.js Dashboard ของคุณอยู่ในโฟลเดอร์ `dashboard` ไม่ได้อยู่ที่ Root ของ Repository

### 4. ตั้ง Environment Variables

ก่อน Deploy ให้เปิดส่วน

**Environment Variables**

แล้วเพิ่ม:

```env
NEXT_PUBLIC_SUPABASE_URL=<Project URL ของคุณ>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon public key ของคุณ>
```

โดยใช้ค่าเดียวกับที่ได้จาก Supabase

### 5. Deploy

กด:

**Deploy**

โดยปกติจะใช้เวลาประมาณ **1 นาที**

### 6. เปิด Dashboard

หลัง Deploy เสร็จ คุณจะได้ URL ประมาณ:

```text
https://your-project.vercel.app
```

เปิด URL นี้ใน Browser

ตอนแรก Dashboard อาจยังว่างอยู่ เพราะยังไม่มี Inspection เข้ามา

### 7. ทดสอบ Realtime

กลับไปที่ Desktop App แล้วทำ Inspection อีกครั้ง

จากนั้นดู Dashboard

ข้อมูลใหม่ควรปรากฏขึ้นบน Dashboard **โดยไม่ต้อง Refresh หน้าเว็บ**

นี่เป็นการทดสอบว่า **Supabase Realtime Subscription** ทำงานถูกต้อง

---

## หลังจากนี้ระบบจะทำงานแบบอัตโนมัติ

เมื่อทุกอย่างตั้งค่าเสร็จแล้ว:

```text
คุณแก้ Code
     ↓
git push
     ↓
GitHub
     ↓
CI ตรวจสอบ Code
     ↓
Vercel ตรวจพบการ Push
     ↓
Deploy Dashboard ใหม่อัตโนมัติ
```

ดังนั้นทุกครั้งที่คุณ:

```bash
git push origin main
```

Vercel จะ Deploy Dashboard เวอร์ชันใหม่ให้อัตโนมัติ

นี่คือ **CD Pipeline สำหรับ Web Dashboard**

และไม่จำเป็นต้องสร้าง GitHub Actions เพิ่มสำหรับ Vercel เพราะ Vercel จัดการ GitHub Integration ให้เอง

---

# Part 5 — CD สำหรับ Desktop App (.exe)

ส่วนนี้ถูกเตรียมไว้ให้แล้วในไฟล์:

```text
.github/workflows/build-release.yml
```

Workflow นี้จะ **ไม่ทำงานทุกครั้งที่ Push**

แต่จะทำงานเมื่อคุณสร้าง **Version Tag**

เหตุผลคือคุณไม่ต้องการสร้าง `.exe` ใหม่ทุกครั้งที่แก้ Code เล็ก ๆ น้อย ๆ

## ตั้งค่าครั้งแรก (ต้องทำก่อนสร้าง Tag ครั้งแรก)

ไฟล์โมเดล `models/*.h5` ถูก `.gitignore` ไว้ (ไฟล์ใหญ่ ~50 MB ต่อไฟล์) ดังนั้น GitHub Actions **จะไม่มีโมเดล** ถ้าไม่อัปโหลดไว้ให้ก่อน

### 1. อัปโหลดโมเดลเป็น GitHub Release ชื่อ `models-v1`

ไปที่ GitHub Repository → **Releases** → **Draft a new release**

* **Choose a tag** → พิมพ์ `models-v1` → **Create new tag**
* Title: `Models v1`
* ลากไฟล์ 2 ไฟล์นี้ใส่ช่อง Attach binaries:
  * `models/defect_model.h5`
  * `models/r2unet__model_underbody_screw.h5`
* กด **Publish release**

> **คำเตือน:** Repo นี้เป็น **Public** แปลว่าใครก็ดาวน์โหลดโมเดลจาก Release ได้ ถ้าไม่อยากให้โมเดลเป็นสาธารณะ ให้เปลี่ยน Repo เป็น Private ก่อน (Settings → General → Danger Zone → Change visibility)

> Tag `models-v1` ไม่ตรงรูปแบบ `v*.*.*` จึงไม่ไป Trigger การ Build .exe

### 2. (ไม่บังคับ) ใส่ Supabase Keys เป็น Repository Secrets

ถ้าอยากให้ `.exe` ที่ Build ออกมา **Sync ขึ้น Cloud ได้ทันที** ไม่ต้องสร้าง `.env` เอง:

GitHub Repository → **Settings → Secrets and variables → Actions → New repository secret**

* `SUPABASE_URL` = Project URL
* `SUPABASE_ANON_KEY` = anon public key

> **คำเตือน:** ถ้าใส่ Secrets ไฟล์ `.env` จะอยู่ในไฟล์ zip บน Release ซึ่ง Repo Public = ใครก็โหลดได้ anon key ก็เปิดเผยอยู่แล้วบน Dashboard ของ Vercel แต่ต้องเข้าใจว่าใครก็ Insert ข้อมูลเข้าตารางได้ (ตาม RLS ใน `schema.sql`)
>
> ถ้าไม่ใส่ Secrets: `.exe` จะทำงาน Offline จนกว่าจะเอาไฟล์ `.env` ไปวางข้าง `R2UNET_Inspection_Pro.exe`

## สร้าง Release

เมื่อคุณต้องการออก Version ใหม่ ให้รัน:

```bash
git tag v1.0.0
git push origin v1.0.0
```

จากนั้นเข้า GitHub Repository → **Actions**

คุณจะเห็น Workflow:

```text
CD - Build & Release Desktop App
```

กำลังทำงาน

ระบบจะใช้ Windows Runner และ PyInstaller เพื่อ Build โปรแกรม ซึ่งอาจใช้เวลาหลายนาที

เมื่อเสร็จแล้วให้ไปที่:

**GitHub → Releases**

คุณจะพบไฟล์ `.zip` ที่ภายในมีไฟล์ `.exe` ที่ Build เสร็จแล้วแนบไว้ให้อัตโนมัติ

---

# Part 6 — CT (Retraining โมเดล)

ส่วนนี้ยัง **ไม่ได้เชื่อมแบบสมบูรณ์ 100%**

เพราะต้องใช้สิ่งที่มีเฉพาะในโปรเจกต์จริงของคุณ ได้แก่:

* Dataset สำหรับ Training จริง
* Architecture ของ R2U-Net จริง

ซึ่งไม่ได้รวมอยู่ในข้อมูลที่ให้มาก่อนหน้านี้

แต่ส่วนระบบถูกเตรียมไว้ให้แล้ว

มีไฟล์ดังนี้:

### `training/evaluate.py`

ไฟล์นี้ทำงานได้แล้ว

ใช้สำหรับเปรียบเทียบโมเดล `.h5` จำนวน 2 ตัวกับ Validation Set

โดยใช้ `dice_coeff` ตัวเดียวกับที่ Production ใช้อยู่

และ Pipeline จะ Fail หากโมเดลใหม่มีผลลัพธ์แย่กว่าโมเดลเดิม

---

### `training/retrain.py`

เป็น **Scaffold สำหรับ Retraining**

ตอนนี้มีโมเดลขนาดเล็กตัวอย่างอยู่ และมีตำแหน่ง `TODO` ระบุไว้อย่างชัดเจนว่าต้องนำ:

* Architecture จริง
* Data Loader จริง

มาใส่ตรงไหน

---

### `.github/workflows/retrain.yml`

เป็น Workflow สำหรับ CT ที่สามารถเรียกใช้ด้วยตัวเอง

ไปที่:

**GitHub → Actions → CT - Retrain & Evaluate → Run workflow**

ระบบจะ:

1. Train โมเดล
2. Evaluate โมเดล
3. เปรียบเทียบคะแนน
4. Upload Candidate Model เป็น Artifact ให้ดาวน์โหลดไปตรวจสอบ

---

# สิ่งที่ต้องทำให้ CT ใช้งานจริง

ก่อนกด **Run workflow** ให้ทำตามนี้:

### 1. ใส่ Architecture จริง

เปิด:

```text
training/retrain.py
```

แล้วเติมฟังก์ชัน:

```python
build_model()
```

ด้วย Architecture R2U-Net จริงของคุณ

หรือใช้วิธีเดียวกับที่คุณใช้สร้าง:

```text
defect_model.h5
```

เดิม

---

### 2. ใส่ Data Loader จริง

เติม:

```python
load_training_data()
```

หาก Dataset ของคุณไม่ได้อยู่ในรูปแบบ:

```text
images/
masks/
```

ให้แก้ Data Loader ให้ตรงกับโครงสร้าง Dataset จริงของคุณ

สามารถดูรายละเอียดเพิ่มเติมได้ที่:

```text
training/README.md
```

---

### 3. เตรียม Dataset แล้วอัปโหลดเป็น GitHub Release ชื่อ `dataset-v1`

`retrain.yml` จะดาวน์โหลด Dataset จาก Release นี้อัตโนมัติ (Dataset ไม่ควรอยู่ใน Git)

สร้างไฟล์ zip **ชื่อตามโมเดล**:

* `defect_dataset.zip` — สำหรับ Pipe Staple
* `tank_screw_dataset.zip` — สำหรับ Underbody Screw

ภายใน zip ต้องมีโครงสร้างแบบนี้ (อยู่ชั้นบนสุดของ zip เลย ไม่มีโฟลเดอร์ครอบ):

```text
train/images/0001.png
train/masks/0001.png      ← ชื่อไฟล์ตรงกับรูปใน images, เป็น mask ขาวดำ
val/images/...
val/masks/...
```

Validation ประมาณ **หลักสิบรูป** ก็เพียงพอสำหรับ Demonstration ของระบบ Gate

จากนั้นสร้าง Release ใหม่ tag `dataset-v1` แล้วแนบไฟล์ zip (วิธีเดียวกับ `models-v1` ใน Part 5)

> **คำเตือน:** Repo Public = Dataset ก็เป็นสาธารณะด้วย ถ้า Dataset เป็นข้อมูลของบริษัท/โรงงาน **อย่าอัปโหลด** จนกว่าจะเปลี่ยน Repo เป็น Private หรือขออนุญาตเจ้าของข้อมูลแล้ว

---

### 4. ทดสอบ Workflow

หลังจากเติมทุกอย่างแล้ว ให้กลับไปที่:

**GitHub → Actions → CT - Retrain & Evaluate → Run workflow**

เมื่อทำงานเสร็จ ให้ดูที่หน้า **Summary**

`evaluate.py` จะสร้างผลลัพธ์เปรียบเทียบ Dice Score และระบุว่า:

```text
PASS
```

หรือ

```text
FAIL
```

---

# ทำไมการ Deploy โมเดลใหม่ถึงยังต้องใช้คนตรวจสอบ?

ระบบนี้ตั้งใจออกแบบให้มี **Human-in-the-loop**

แม้ทุกอย่างจะถูกตั้งค่าเสร็จแล้ว การนำ Candidate Model ไปแทนที่ Model ที่ Production ใช้อยู่ **ยังต้องทำด้วยตัวเอง**

ขั้นตอนคือ:

```text
Retrain
   ↓
Evaluate
   ↓
ผ่าน Gate
   ↓
Download Candidate Model
   ↓
ตรวจสอบโมเดลด้วยตัวเอง
   ↓
นำไปแทนที่โมเดลใน models/
   ↓
สร้าง Version Tag
   ↓
Build .exe Release
```

นี่เป็น **การออกแบบโดยตั้งใจ ไม่ใช่ข้อจำกัดของระบบ**

เพราะไม่ควรให้ Pipeline เปลี่ยนโมเดลตรวจจับ Defect ใน Production โดยอัตโนมัติโดยที่ไม่มีคนตรวจสอบก่อน แม้จะเป็นโปรเจกต์สำหรับ Demo หรือโปรเจกต์มหาวิทยาลัยก็ตาม

---

# Quick Checklist — เช็กลิสต์ทั้งหมด

### Supabase

* [/] สร้าง Supabase Project แล้ว
* [/] รัน `schema.sql` แล้ว
* [/] เปิด Realtime สำหรับ `inspections` แล้ว
* [/] ได้ Project URL แล้ว
* [/] ได้ anon public key แล้ว

### Desktop App

* [/] สร้าง `.env`
* [/] ใส่ `SUPABASE_URL`
* [/] ใส่ `SUPABASE_ANON_KEY`
* [/] ตั้ง `DEVICE_ID`
* [/] รัน `pip install -r requirements.txt`
* [/] เปิด App แล้วเห็น `Cloud sync enabled`
* [/] ทดลอง Inspection แล้วเห็น `Synced 1 record(s) to Supabase`
* [/] ตรวจสอบข้อมูลใน Supabase Table Editor แล้ว
* [/] ตรวจสอบว่า `.env` อยู่ใน `.gitignore`

### GitHub / CI

* [/] สร้าง GitHub Repository
* [/] Push Code ขึ้น GitHub
* [/] CI Workflow ทำงาน
* [/] CI ขึ้นสถานะสีเขียว

### Vercel / Web CD

* [/] สร้าง Vercel Project
* [/] เชื่อมกับ GitHub Repository
* [/] ตั้ง Root Directory เป็น `dashboard`
* [/] ตั้ง `NEXT_PUBLIC_SUPABASE_URL`
* [/] ตั้ง `NEXT_PUBLIC_SUPABASE_ANON_KEY`
* [/] Deploy สำเร็จ
* [/] เปิด Dashboard ได้
* [/] ทดลอง Inspection จริง
* [/] ข้อมูลปรากฏบน Dashboard แบบ Realtime โดยไม่ต้อง Refresh

### อัปเดตหลังแก้โค้ดรอบล่าสุด

* [ ] รัน `supabase/migrations/001_local_id_dedup.sql` ใน Supabase SQL Editor
* [ ] (ไม่บังคับ) แก้เวลาข้อมูลเก่าที่เพี้ยน 7 ชม. (คำสั่งท้ายไฟล์ migration)
* [ ] `pip install -r requirements.txt` ใหม่ (ล็อกเวอร์ชันแล้ว)
* [ ] Commit + Push แล้วดูว่า CI และ Dashboard CI เป็นสีเขียว

### Desktop CD

* [ ] อัปโหลดโมเดล 2 ไฟล์ไปที่ Release `models-v1`
* [ ] (ไม่บังคับ) ตั้ง Secrets `SUPABASE_URL` / `SUPABASE_ANON_KEY`
* [ ] สร้าง Tag เช่น `v1.0.0`
* [ ] Push Tag ขึ้น GitHub
* [ ] `CD - Build & Release Desktop App` ทำงานสำเร็จ
* [ ] ตรวจสอบ `.exe` ใน GitHub Releases

### CT / Retraining

* [ ] ใส่ R2U-Net Architecture จริงใน `build_model()`
* [ ] ใส่ Data Loader จริงใน `load_training_data()`
* [ ] เตรียม Dataset zip แล้วอัปโหลดไปที่ Release `dataset-v1`
* [ ] ทดสอบ `CT - Retrain & Evaluate`
* [ ] ตรวจสอบ Dice Score
* [ ] ตรวจสอบ Candidate Model ด้วยตัวเองก่อนนำไป Production
