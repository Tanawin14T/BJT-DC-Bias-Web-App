# BJT DC Bias Web App — ENG29 2121 Lab 02

Flask web application ที่คำนวณ DC operating point ของวงจร BJT Common-Emitter
แบบ Voltage-Divider Bias ด้วยแบบจำลอง Forward-Active (β คงที่, V<sub>BE</sub> คงที่)

- อินพุต: `VCC` [V], `R1`, `R2`, `RC`, `RE` [kΩ], `β`, `VBE` [V]
- เอาต์พุต: `VB`, `VE`, `VC`, `VCE` [V], `IC` [mA], `IB` [µA], `IE` [mA]
  พร้อม `VTH`, `RTH` และสถานะการทำงาน (Forward Active / Cutoff / Saturation)

## โครงสร้างไฟล์

```
app.py                  Flask routes (HTTP เท่านั้น)
dc_bias.py              การคำนวณและ validation (ไม่ import Flask)
templates/index.html    ฟอร์ม + ตารางผลลัพธ์ (Jinja)
static/style.css        หน้าตา
tests/test_dc_bias.py   unit tests เชิงวิศวกรรม
tests/test_web.py       HTTP tests ด้วย Flask test client
docs/                   validation, design note, reflection
```

## ติดตั้ง

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

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

ผลที่คาดหวัง: 11 tests ผ่านทั้งหมด (8 tests ด้านวิศวกรรม + 3 tests ด้าน HTTP)

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

## ข้อจำกัดของแบบจำลอง

- ใช้ Forward-Active approximation: VBE คงที่ และ β คงที่ ไม่ขึ้นกับ IC หรืออุณหภูมิ
- ไม่ใช่ SPICE/ngspice และไม่มีผลกระทบจาก Early effect, leakage, nonlinear rπ
- เมื่อ `VTH ≤ VBE` (Cutoff) หรือ `VCE ≤ 0.20 V` (Saturation) เว็บจะแสดงคำเตือน
  เพราะสมการ `IC = β·IB` ใช้ไม่ได้ในโหมดเหล่านั้น
