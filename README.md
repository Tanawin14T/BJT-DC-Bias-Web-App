# BJT DC Bias Web App + CE Simulator — ENG29 2121 Lab 03/04

Flask web application ที่คำนวณ DC operating point ของวงจร BJT Common-Emitter
สามแบบ ด้วยแบบจำลอง Forward-Active (β คงที่, V<sub>BE</sub> คงที่)

| โหมด | อินพุตที่ใช้ | สมการกระแสเบส |
|------|-------------|----------------|
| `Fixed Bias` | `VCC`, `RB`, `RC`, `β`, `VBE` | `IB = (VCC − VBE) / RB` (Emitter ต่อกราวด์, `VE = 0`) |
| `Emitter Bias` | `VCC`, `RB`, `RC`, `RE`, `β`, `VBE` | `IB = (VCC − VBE) / [RB + (β+1)RE]` |
| `Voltage Divider Bias` | `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE` | `IB = (VTH − VBE) / [RTH + (β+1)RE]` |

ความต้านทานแต่ละช่องเลือกหน่วยได้ **Ω / kΩ / MΩ** (ค่าเริ่มต้น kΩ) โปรแกรมแปลงเป็น kΩ ก่อนส่งเข้า `dc_bias.py` (ตารางผลแสดง RTH เป็น Ω/kΩ/MΩ อัตโนมัติ) ผลลัพธ์: `VB`, `VE`, `VC`, `VCE` [V],
`IC` [mA], `IB` [µA], `IE` [mA] พร้อม `VTH`, `RTH` และสถานะการทำงาน
(Forward Active / Cutoff / Saturation) เลือกโหมดจาก dropdown บนฟอร์ม —
ช่องที่ไม่เกี่ยวข้องจะถูกซ่อน และโหมด Divider ให้ผลเหมือน Lab 2 ทุกประการ

## โครงสร้างไฟล์

```
app.py                  Flask routes (HTTP เท่านั้น)
dc_bias.py              การคำนวณ DC แบบ Analytical (ไม่ import Flask)
spice_engine.py         Lab 04: validate → netlist → subprocess ngspice → parse raw
plots.py                Lab 04: SVG จากข้อมูลจริง (ไม่มี chart library)
templates/index.html    ฟอร์ม Lab 03 + ฟอร์ม/ผล Lab 04 (Jinja)
static/style.css        หน้าตา (responsive)
tests/test_dc_bias.py   unit tests เชิงวิศวกรรม Lab 03
tests/test_web.py       HTTP tests ด้วย Flask test client
tests/test_spice_engine.py  netlist/parser/error-path tests (ไม่ต้องมี ngspice)
tests/test_sim_web.py   HTTP tests ของ /simulate (stub engine)
docs/                   validation, design note, reflection, screenshots
```

## ติดตั้ง

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

สำหรับ Simulator ต้องมี **ngspice (โปรแกรมภายนอก ไม่ใช่ pip package)**:
ดาวน์โหลดจาก <https://ngspice.sourceforge.io/download.html>, ติดตั้งแล้วตรวจ
`ngspice --version` ให้ขึ้นก่อนรัน Flask ถ้า executable ไม่ได้อยู่ใน PATH ให้ตั้ง
`$env:NGSPICE_PATH = "C:\path\to\ngspice.exe"` (Windows) หรือ `export NGSPICE_PATH=...`
(bash) — adapter จะแจ้ง error ชัดเจนถ้าเรียก engine ไม่ได้ หรือไม่คืนกราฟเก่าเป็นผลสำเร็จ

## รันเว็บ

```powershell
python -m flask --app app run --debug
```

เปิด <http://127.0.0.1:5000/> — ต้องรันผ่าน Flask เท่านั้น การ double-click
`templates/index.html` จะไม่ทำงาน เพราะไม่มี Python backend

## ทดสอบ

```powershell
python -m unittest discover -s tests -v
```

ผลที่คาดหวัง: 40 tests ผ่านทั้งหมด (13 tests Lab 2/3 เดิม + 27 tests ของ SPICE adapter/web)

## ค่าตัวอย่างและผลอ้างอิง

VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

| ปริมาณ | ค่า |
|--------|-----|
| VTH | 2.164 V |
| RTH | 18.033 kΩ |
| IB | 12.299 µA |
| IC | 1.230 mA |
| IE | 1.242 mA |
| VE | 1.242 V |
| VB | 1.942 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| Region | Forward Active |

การคำนวณมือทีละขั้นอยู่ใน [`docs/validation.md`](docs/validation.md)

## หลักฐานการทดสอบ

- ภาพหน้าจอผลการคำนวณ: [`docs/screenshots/dc-bias-result.jpg`](docs/screenshots/dc-bias-result.jpg)
- บันทึกผลรันเทสต์ (13 tests): [`docs/test-log.txt`](docs/test-log.txt)

## ข้อจำกัดของแบบจำลอง

- ใช้ Forward-Active approximation: VBE คงที่ และ β คงที่ ไม่ขึ้นกับ IC หรืออุณหภูมิ
- ไม่ใช่ SPICE/ngspice และไม่มีผลกระทบจาก Early effect, leakage, nonlinear rπ
- เมื่อ `VTH ≤ VBE` (Cutoff) หรือ `VCE ≤ 0.20 V` (Saturation) เว็บจะแสดงคำเตือน
  เพราะสมการ `IC = β·IB` ใช้ไม่ได้ในโหมดเหล่านั้น

## Lab 04 — CE Amplifier Simulator (ngspice)

ส่วนนี้ต่อยอดจาก Lab 3 **โดยไม่ลบ DC Bias ทั้ง 3 แบบ** ฟอร์มด้านล่างของหน้าเว็บ
(`#simulator`) ส่งพารามิเตอร์ที่ตรวจแล้วไปยัง `spice_engine.py` ซึ่งสร้าง netlist
ของวงจร CE Voltage Divider อ้างอิงแล้วเรียก ngspice แบบ Batch ผ่าน
`subprocess.run([...], cwd=<tempdir>, timeout=30)` (ไม่ใช้ `shell=True`) และอ่าน
`run.raw` ที่ engine เขียนจริง

| Analysis | คำสั่ง | ผลที่แสดง |
|----------|--------|-----------|
| DC | `.op` | VB, VE, VC, VCE, IC (อ่านจาก `v(vb)`, `v(e)`, `v(c)`, `i(vic)`) |
| AC | `.ac dec N fstart fstop` | Bode: Gain = \|Vout(out)/Vin(vb)\| [dB], Phase [deg] พร้อม f3dB หรือข้อความว่าไม่พบในช่วง sweep |
| Transient | `.tran TSTEP TSTOP` (step ก่อน stop ตามไวยากรณ์ ngspice) | Vin(vb)/Vout(out) ตามเวลา [ms], AC amplitude (หัก DC), Gain estimate และทิศทางเฟส |

**Input fixture ตั้งต้น:** VCC 12 V · R1 100 kΩ · R2 22 kΩ · RC 2.2 kΩ ·
RE 1 kΩ · RL 10 kΩ · Cin = Cout = 10 µF · source 10 mV peak @ 1 kHz ·
BJT model `QCE_GENERIC` = `NPN(IS=1E-14 BF=200 VAF=100 RB=10 CJC=3.5P CJE=8P TF=400P)`
(โมเดล generic ที่ระบุพารามิเตอร์ไว้ใน `spice_engine.py` ไม่ได้อ้างรุ่นเฉพาะ —
เปลี่ยนตาม Starter Kit ของผู้สอนได้ที่จุดเดียว) **ไม่มี Emitter bypass capacitor**
ใน baseline ตามใบงาน

**ที่มาของผล (provenance):** หน้าผลแสดง engine, status, model และ netlist/log
จากรันนั้น ผล Analytical จาก `dc_bias.py` ยังอยู่แยกต่างหากในส่วน Lab 03 —
ตัวเลขสองชุดนี้มีสมมติฐานต่างกัน (β/VBE คงที่ vs BJT model ของ SPICE) จึงไม่บังคับให้เท่ากัน
หาก ngspice หาย, รันfailed, timeout หรือ raw ว่าง หน้าเว็บจะแสดง error และจะไม่แสดง
กราฟ/ผลสำเร็จปลอม

**สถานะเครื่องที่ใช้ตรวจ:** ติดตั้ง ngspice-47 (console) แล้วที่
`C:\Users\B6808778\AppData\Local\ngspice-47\Spice64\bin\ngspice_con.exe` และตั้ง
`NGSPICE_PATH` ระดับผู้ใช้; รัน DC/AC/Transient จริงผ่านหน้าเว็บแล้ว ดูผล B1–B8
(รวม B3 ทั้ง Fixed/Emitter/Divider + SPICE, B4 AC/Bode, B5/B6 Transient ทั้ง 3 โหมด, และ B8 desktop + narrow iframe 390 px) พร้อม screenshot และข้อความ error ก่อนติดตั้ง engine ได้ใน
[`docs/validation.md`](docs/validation.md) (Playwright MCP ไม่มีใน session นี้
จึงบันทึก NOT RUN และใช้ OpenCode Browser Tool แทน — ไม่ได้อ้างว่าเป็น Playwright)

## สิ่งที่ AI แก้ vs สิ่งที่ตรวจเอง

- AI (OpenCode) เพิ่ม `spice_engine.py`, `plots.py`, route `/simulate`, UI และ tests
  ตามข้อกำหนด Lab 04 โดยคง `dc_bias.py`, ฟอร์ม Lab 03 และ tests เดิมไว้ครบ
- ผู้ใช้ตรวจ/อนุมัติขอบเขตงาน เลือกแนวทาง "adapter + NOT RUN" เมื่อยังไม่มี ngspice
  และยืนยันให้ commit/push ขึ้น `main`; หลังติดตั้ง engine จึงอัปเดตผลเป็น B1–B8
- ผลคำนวณ Lab 03 เทียบมือแล้วใน `docs/validation.md`; หน้าเว็บตรวจใน browser จริง
  ทั้ง error path (ก่อนมี engine) และรัน DC/AC/Transient จริงหลังติดตั้ง ngspice-47
- หลักฐาน status และ screenshot อยู่ใน `docs/validation.md` และ
  `docs/screenshots/lab04-engine-error-desktop.png`
