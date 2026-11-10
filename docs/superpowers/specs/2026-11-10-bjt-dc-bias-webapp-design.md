# Design — BJT DC Bias Web App (Lab 02, ENG29 2121)

วันที่: 2026-11-10
สถานะ: รออนุมัติ
เจ้าของ: Tanawin (นักศึกษา) + OpenCode/Superpowers

## 1. Intent และเหตุผล

Lab 02 ต้องการให้เห็นความต่างระหว่าง "ไฟล์ HTML ที่เปิดตรง ๆ" กับ "เว็บที่มี Python
backend ทำงานจริง" ภายในคาบเดียว (180 นาที) ผลลัพธ์คือ Flask web app ที่รับค่าอุปกรณ์
ของวงจร BJT Common-Emitter แบบ Voltage-Divider Bias แล้วให้ Python คำนวณ DC
operating point จริง (ไม่ใช่ค่าที่ฮาร์ดโค้ดใน HTML) พร้อม validation, คำเตือนเมื่อ
แบบจำลอง Forward-Active ใช้ไม่ได้, automated tests และ commit ขึ้น GitHub

คุณค่าที่ต้องการ: นักศึกษาเข้าใจเส้นทาง Browser → HTTP → Flask route → ฟังก์ชัน
วิศวกรรม → HTML response และเป็นผู้ตรวจสอบผลคำนวณเอง ไม่ใช่เชื่อ AI

## 2. Goals

- G1 เปิดผ่าน `http://127.0.0.1:5000/` แล้วเห็นฟอร์มกรอกค่า 7 ตัว พร้อมหน่วยกำกับ
- G2 กด Calculate แล้วได้ VB, VE, VC, VCE [V], IC [mA], IB [µA], IE [mA] จาก Python จริง
- G3 แสดงสถานะการทำงาน (Forward Active / Cutoff / Saturation) และคำเตือนเมื่ออยู่นอกสมมติฐาน
- G4 ข้อมูลผิด (ค่าว่าง, ไม่ใช่ตัวเลข, R≤0, β≤0, VCC≤0) แสดง error ที่อ่านรู้เรื่อง หน้าไม่ล้ม
- G5 มี automated tests ≥3 ตัวสำหรับคณิตศาสตร์วิศวกรรม + ≥1 ตัวผ่าน Flask test client
- G6 clone repo แล้วทำตาม README เพื่อติดตั้ง/รัน/ทดสอบได้จริง

## 3. Non-goals

- AC small-signal, gain, Bode plot, transient, signal generator, overlay animation
- DC load line, กราฟใด ๆ, SPICE/ngspice integration
- Bias ชนิดอื่น (Fixed, Emitter bias) — อยู่ใน W3
- ฐานข้อมูล, authentication, deployment, Docker, CI
- JavaScript framework หรือ frontend build tool

## 4. Anti-goals (ทำงานได้แต่ถือว่าล้มเหลว)

- ตัวเลขผลลัพธ์ถูกฝังใน HTML/template หรือคำนวณใน Jinja
- `templates/index.html` ถูกเปิดด้วย `file://` แล้วดูเหมือนใช้งานได้
- คำนวณต่อแม้ VTH ≤ VBE หรือ VCE ≤ VCE,sat แล้วรายงานเป็นค่าที่เชื่อถือได้โดยไม่มีคำเตือน
- test ที่ assert ค่าที่ตัวเองคำนวณผิด หรือ test ที่ไม่ได้รันจริงแล้วอ้างว่าผ่าน
- commit `.venv/`, `__pycache__/`, `.env`
- สมการฟิสิกส์ไปอยู่ใน `app.py` หรือ template

## 5. Constraints

- เวลาทำจริง ~75 นาทีสำหรับ build + 25 นาทีตรวจสอบ (timebox ของ Lab)
- Python 3.14.2 (ติดตั้งอยู่), Flask 3.x, ไลบรารีมาตรฐาน `unittest` (ไม่เพิ่ม pytest)
- รันเฉพาะ localhost, Windows, ไม่ต้องมีอินเทอร์เน็ตตอนรัน
- ต้องใช้ `python -m unittest discover -s tests -v` ได้ตามใบงาน
- โฟลเดอร์ repo มีช่องว่างในชื่อ (`BJT DC Bias Web App`) → ทุกคำสั่ง shell ต้อง quote path

## 6. Approaches ที่พิจารณา

| ทาง | ลักษณะ | ข้อดี | ข้อเสีย | สรุป |
|-----|--------|-------|---------|------|
| A | Server-rendered form: `POST /calculate` → render `index.html` พร้อมผล | โค้ดน้อย, test ง่ายด้วย Flask client, ไม่มี JS ที่พังเงียบ | หน้าฟอร์ม refresh, ต่อยอด interactive ต้องรื้อ frontend later | **เลือก** |
| B | JSON API `POST /calculate` + `fetch()` อัปเดต DOM | เป็นฐานของ roadmap W5–W7 (knob, กราฟ) | เพิ่ม JS + contract + test, เสี่ยงเวลาไม่พอ | ไม่เลือก |
| C | Flask + WTForms + Blueprint แยกโมดูลเต็ม | โครงสร้างระดับ production | งานเอกสารมาก ไม่ได้คะแนนเพิ่ม | ตัดทิ้ง |

เหตุผลที่เลือก A: เป้าหมายการเรียนรู้คือ "request ไปคำนวณที่ Python จริง" ไม่ใช่
สถาปัตยกรรม production และเหลือเวลาไปทำ validation/warning/tests ซึ่งมีคะแนน 4/10

## 7. การตัดสินใจที่ตกลงแล้ว

### 7.1 หน่วยอินพุต
ผู้ใช้กรอกตัวต้านทานเป็น **kΩ** (100, 22, 2.2, 1) ตามค่าตัวอย่างในใบงานและภาพ preview
แปลงเป็น Ω **จุดเดียว** ใน `dc_bias.py` (ค่าคงที่ `KOHM_TO_OHM = 1000.0`) แล้วคำนวณ
ต่อในหน่วยฐาน SI. หน่วยที่แสดงผล: V, mA, µA, kΩ (RTH)

### 7.2 โครงสร้างไฟล์
```
app.py                      # Flask routes + การ map error → HTTP
dc_bias.py                  # ฟิสิกส์/การคำนวณ/validation (ไม่ import flask)
templates/index.html        # ฟอร์ม + ผลลัพธ์ (Jinja) ไม่มีสมการฟิสิกส์
static/style.css            # หน้าตา
tests/test_dc_bias.py       # unit tests เชิงวิศวกรรม
tests/test_web.py           # HTTP tests ด้วย Flask test client
requirements.txt            # Flask==3.1.*
README.md                   # วิธีติดตั้ง/รัน/ทดสอบ + ผลอ้างอิง
AGENTS.md                   # กติกาสำหรับ AI agent ใน repo นี้
docs/validation.md          # การคำนวณมืออิสระ + ตารางเทียบกับผลเว็บ
docs/design-note.md         # สรุป design นี้ฉบับย่อ
docs/reflection.md          # คำตอบคำถามรายบุคคลท้ายใบงาน
docs/superpowers/specs/2026-11-10-bjt-dc-bias-webapp-design.md
```

### 7.3 HTTP contract
| Method | Path | พฤติกรรม |
|--------|------|----------|
| GET | `/` | 200, ฟอร์มเปล่า/ค่าเริ่มต้นตัวอย่าง, ไม่มีผลลัพธ์ |
| POST | `/calculate` | สำเร็จ → 200 + หน้าเดิมพร้อมผล; ข้อมูลผิด → 400 + หน้าเดิมพร้อม error และคงค่าที่กรอกไว้ |

เลือก `POST /calculate` (ไม่ใช่ `POST /`) เพื่อให้ route อ่านง่ายและ test แยกได้ชัด

### 7.4 API ของ `dc_bias.py`
```python
KOHM_TO_OHM = 1000.0
VCE_SAT = 0.20          # V, เกณฑ์ saturation ที่ประกาศไว้ใน docs/validation.md

@dataclass(frozen=True)
class DcBiasInput:      # ทุกค่าเป็น float, R เป็น kΩ
    vcc: float; r1: float; r2: float; rc: float; re: float; beta: float; vbe: float

@dataclass(frozen=True)
class DcBiasResult:
    vth: float; rth: float                 # V, kΩ
    ib_ua: float; ic_ma: float; ie_ma: float
    vb: float; ve: float; vc: float; vce: float
    region: str                            # "Forward Active" | "Cutoff" | "Saturation"
    warnings: tuple[str, ...]              # ข้อความเตือนที่แสดงบนหน้าเว็บ

def parse_inputs(raw: Mapping[str, str]) -> tuple[DcBiasInput | None, dict[str, str]]
def calculate(inp: DcBiasInput) -> DcBiasResult
```
`parse_inputs` รับค่าเป็น string จากฟอร์ม, คืน (input, errors) โดย `errors` เป็น
`{field_name: message}`. ไม่มี dependency ต่อ Flask/HTML

### 7.5 Validation rules
| เงื่อนไข | ผล |
|----------|-----|
| ช่องว่าง / ไม่ใช่ตัวเลข / `nan` / `inf` | error รายช่อง "กรุณากรอกตัวเลข" |
| VCC ≤ 0 | error "VCC ต้องมากกว่า 0" |
| R1, R2, RC, RE ≤ 0 | error "ค่าความต้านทานต้องมากกว่า 0" |
| β ≤ 0 | error "β ต้องมากกว่า 0" |
| VBE ≤ 0 | error "VBE ต้องมากกว่า 0" |
| β > 1000 หรือ β < 10 | ไม่ error แต่มี warning ว่าแบบจำลองอาจคลาดเคลื่อน |
| VBE นอกช่วง 0.5–0.9 V | warning |

### 7.6 Region logic (ลำดับที่แน่นอน)
1. คำนวณ `VTH = VCC·R2/(R1+R2)`, `RTH = R1R2/(R1+R2)`
2. ถ้า `VTH ≤ VBE` → **Cutoff**: IB = IC = IE = 0, VE = 0, VB = VTH, VC = VCC, VCE = VCC
   พร้อม warning ว่าวงจรไม่อยู่ใน Forward Active
3. ไม่งั้นคำนวณ `IB = (VTH−VBE)/(RTH+(β+1)RE)`, `IC = β·IB`, `IE = (β+1)·IB`,
   `VE = IE·RE`, `VB = VE+VBE`, `VC = VCC−IC·RC`, `VCE = VC−VE`
4. ถ้า `VCE ≤ VCE_SAT` หรือ `VCE < 0` → **Saturation**: แสดงค่าที่คำนวณได้แต่ระบุชัดว่า
   `IC = β·IB` ใช้ไม่ได้ในโหมดนี้ และแจ้งขอบเขต `IC,max ≈ (VCC−VCE_SAT)/(RC+RE)`
5. ไม่งั้น → **Forward Active** ไม่มี warning

### 7.7 ผลอ้างอิง (ใช้ใน test และ README)
VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V

| ปริมาณ | ค่า |
|--------|-----|
| VTH | 2.164 V |
| RTH | 18.033 kΩ |
| IB | 12.299 µA |
| IC | 1.2299 mA |
| IE | 1.2422 mA |
| VE | 1.2422 V |
| VB | 1.9422 V |
| VC | 9.2943 V |
| VCE | 8.0522 V |
| Region | Forward Active |

Tolerance ใน test: `assertAlmostEqual(..., places=2)` หรือ relative 0.5%

### 7.8 UI
- ฟอร์มกริด 2 คอลัมน์บนจอใหญ่, 1 คอลัมน์บนมือถือ (CSS ธรรมดา, ไม่มี framework)
- ป้ายหน่วยใน label: `VCC (V)`, `R1 (kΩ)`, `β`, `VBE (V)`
- หลังคำนวณ: กล่องสถานะสี (เขียว = active, เหลือง = saturation, แดง = cutoff/error)
  แล้วตามด้วยตารางผลลัพธ์ที่มีหน่วยทุกแถว
- แถวเสริมท้ายตาราง: VTH, RTH (ช่วยตรวจสอบด้วยมือ)
- ไม่มี JavaScript

### 7.9 Tests (ขั้นต่ำตามใบงาน A6)
`tests/test_dc_bias.py`
1. `test_reference_operating_point` — ชุดค่าตัวอย่าง ตรงกับตาราง 7.7 (ทุกค่า)
2. `test_cutoff_when_vth_below_vbe` — R2 เล็ก (เช่น R1=100k, R2=1k) → region == "Cutoff", IC == 0
3. `test_saturation_when_rc_too_large` — RC=10k, RE=0.1k → region == "Saturation", มี warning
4. `test_unit_conversion` — ป้อน 100 kΩ ให้ผลเท่ากับการคำนวณด้วย 100000 Ω ในสูตร
5. `test_parse_rejects_non_positive_and_non_numeric` — R=0, β=0, "abc", ช่องว่าง → errors ครบ

`tests/test_web.py`
6. `test_get_index_returns_form` — 200 + มี name="vcc" ฯลฯ
7. `test_post_calculate_shows_result` — 200 + ข้อความ "8.05" + "Forward Active"
8. `test_post_invalid_shows_error` — 400 + ข้อความ error, ไม่มี traceback

### 7.10 ความปลอดภัย/สุขอนามัยของ repo
- Flask debug ใช้เฉพาะเครื่องตัวเอง ไม่ผูก `0.0.0.0`
- `.gitignore` กัน `.venv/`, `__pycache__/`, `.env` (มีแล้ว)
- ไม่มี secret ใด ๆ ใน repo

### 7.11 เจ้าของเอกสาร (ตัดสิน 2026-11-10)
`docs/validation.md` และ `docs/reflection.md` ให้ผู้ช่วย (agent) เขียนเนื้อหาเต็มทั้งสองไฟล์
โดย `validation.md` ต้องแสดงการคำนวณมือที่ตรวจย้อนได้จริง และ `reflection.md` ต้องตรงกับ
สิ่งที่ทำจริงในคาบ (นักศึกษาตรวจและปรับถ้อยคำให้เป็นเสียงของตนเองก่อนส่ง)

### 7.12 เผยแพร่ (ตัดสิน 2026-11-10)
สร้าง repo GitHub ชื่อ `bjt-dc-bias-web-app` แบบ public แล้ว push commit ทั้งหมด
(หากยังไม่ได้ sign in GitHub Desktop จะ commit ในเครื่องให้ครบก่อน แล้วแจ้งขั้นตอน publish)

## 8. การแมปเกณฑ์ตรวจรับของใบงาน (A1–A7)

อ้างอิง: ใบงาน ENG29 2121 Lab 02 (ไฟล์ `Lab02_BJT_Simulator_Brainstorm_2-2569.html`)

| เกณฑ์ | ข้อกำหนดในใบงาน | ส่วนของ design ที่รองรับ |
|-------|-----------------|--------------------------|
| A1 | GET / = 200 + เห็นฟอร์ม | 7.3, 7.8, test 6 |
| A2 | POST แล้ว backend คำนวณ ไม่ฮาร์ดโค้ด | 7.3, 7.4, test 7 |
| A3 | VB, VE, VC, VCE, IC ตรงกับการคำนวณอิสระ | 7.7 + `docs/validation.md` |
| A4 | R≤0, β≤0, non-numeric → error ชัด หน้าไม่ล้ม | 7.5, test 8 |
| A5 | warning กรณี Cutoff / Saturation | 7.6, test 2–3 |
| A6 | ≥3 tests คณิตศาสตร์ + ≥1 Flask test client | 7.9 (5 + 3 tests) |
| A7 | clone แล้วติดตั้ง/รัน/ทดสอบได้ตาม README | 7.2 + README |

หมายเหตุ: `VCE,sat` ไม่ได้ระบุตัวเลขในใบงาน — design นี้ประกาศ 0.20 V และบันทึกไว้ใน
`docs/validation.md` เพื่อให้ตรวจสอบย้อนกลับได้ (สอดคล้องข้อ "VCE ต่ำใกล้ saturation")

## 9. สิ่งที่เหลือให้ผู้สร้างตัดสินใจ

- โทนสี/ฟอนต์ละเอียดของ CSS (ใช้ Tahoma/Noto Sans Thai ให้อ่านไทยได้)
- ถ้อยคำภาษาไทยของ label/warning (เอาความหมายตาม 7.5–7.6)
- จะแสดง IB/IE เป็น µA/mA หรือ mA อย่างเดียว (แนะนำตาม 7.1)
- ลำดับหัวข้อใน README
