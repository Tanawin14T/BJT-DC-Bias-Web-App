# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flask multi-file web app ที่คำนวณ DC operating point ของ BJT Common-Emitter Voltage-Divider Bias พร้อม validation, region warning, automated tests และ commit ขึ้น GitHub

**Architecture:** Server-rendered form (approach A). `POST /calculate` → `parse_inputs()` → `calculate()` → Jinja render หน้าเดิมพร้อมผล. ฟิสิกส์ทั้งหมดอยู่ใน `dc_bias.py` ซึ่งไม่ import Flask; `app.py` ทำหน้าที่ HTTP เท่านั้น

**Tech Stack:** Python 3.14.2, Flask 3.1.x, Jinja2, `unittest` (stdlib), CSS ธรรมดา (ไม่มี JS)

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-webapp-design.md`

## Global Constraints

- Python 3.14.2 ที่ `C:\Program Files\Python314` (อยู่ใน user PATH แล้ว)
- Flask `3.1.*` เท่านั้น; ห้ามเพิ่ม dependency อื่น
- test framework: `unittest` — รันด้วย `python -m unittest discover -s tests -v`
- อินพุตตัวต้านทานเป็น **kΩ**, แปลงเป็น Ω ด้วย `KOHM_TO_OHM = 1000.0` จุดเดียวใน `dc_bias.py`
- `VCE_SAT = 0.20` V
- route: `GET /` (200) และ `POST /calculate` (200 สำเร็จ / 400 ข้อมูลผิด)
- ห้ามคำนวณฟิสิกส์ใน `app.py` หรือ template
- path ของ repo มีช่องว่าง → quote ทุกครั้งใน shell
- ค่าอ้างอิง: VCC=12, R1=100, R2=22, RC=2.2, RE=1 (kΩ), β=100, VBE=0.70 →
  VTH 2.164 V, RTH 18.033 kΩ, IB 12.299 µA, IC 1.2299 mA, IE 1.2422 mA,
  VE 1.2422 V, VB 1.9422 V, VC 9.2943 V, VCE 8.0522 V, Forward Active

## Review Focus

- อินพุต `"nan"`, `"inf"`, `"-inf"` — `float()` รับได้ แต่ต้องถูกปฏิเสธเป็น error ไม่ใช่ไหลเข้าสูตร
- ค่าตัวต้านทาน ≤ 0 (โดยเฉพาะ R2=0 หรือ R1=0) — ต้อง error ก่อนถึงการหาร ไม่ใช่ ZeroDivisionError/500
- `RC` ใหญ่จน `VCE` ติดลบ — ต้องรายงาน Saturation + warning ไม่ใช่ตัวเลขที่ดูปกติ
- `VBE ≥ VTH` — ต้องเป็น Cutoff ที่ IB=IC=0 ไม่ใช่ IB ติดลบ
- β นอกช่วงปกติ (เช่น 5 หรือ 2000) — ต้องยังคำนวณได้และมี warning ไม่ crash

---

### Task 1: โครงโปรเจกต์ + โมดูลคำนวณชุดอ้างอิง

**Files:**
- Create: `dc_bias.py`
- Create: `tests/test_dc_bias.py`
- Create: `requirements.txt`
- Create: `tests/__init__.py` (ว่าง — ให้ discover ทำงานสม่ำเสมอ)

**Interfaces:**
- Produces:
  - `KOHM_TO_OHM: float = 1000.0`, `VCE_SAT: float = 0.20`
  - `@dataclass(frozen=True) class DcBiasInput: vcc, r1, r2, rc, re, beta, vbe` (float ทั้งหมด; r* เป็น kΩ)
  - `@dataclass(frozen=True) class DcBiasResult: vth, rth, ib_ua, ic_ma, ie_ma, vb, ve, vc, vce, region, warnings` (`region: str`, `warnings: tuple[str, ...]`)
  - `calculate(inp: DcBiasInput) -> DcBiasResult`

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

`tests/test_dc_bias.py`:
```python
import unittest
from dc_bias import DcBiasInput, calculate

REF = DcBiasInput(vcc=12.0, r1=100.0, r2=22.0, rc=2.2, re=1.0, beta=100.0, vbe=0.70)

class TestReferenceOperatingPoint(unittest.TestCase):
    def test_reference_operating_point(self):
        r = calculate(REF)
        self.assertAlmostEqual(r.vth, 2.164, places=3)
        self.assertAlmostEqual(r.rth, 18.033, places=3)
        self.assertAlmostEqual(r.ib_ua, 12.299, places=3)
        self.assertAlmostEqual(r.ic_ma, 1.2299, places=4)
        self.assertAlmostEqual(r.ie_ma, 1.2422, places=4)
        self.assertAlmostEqual(r.ve, 1.2422, places=3)
        self.assertAlmostEqual(r.vb, 1.9422, places=3)
        self.assertAlmostEqual(r.vc, 9.2943, places=3)
        self.assertAlmostEqual(r.vce, 8.0522, places=3)
        self.assertEqual(r.region, "Forward Active")
        self.assertEqual(r.warnings, ())
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: สร้าง `dc_bias.py`**

`requirements.txt`:
```
Flask==3.1.2
```
`dc_bias.py`: dataclasses ตาม Interfaces, `calculate()` ทำตามลำดับ 7.6 ของ spec
(ขั้นนี้ยังไม่ต้องมี cutoff/saturation — ให้เฉพาะเส้นทาง Forward Active ที่ทำให้ test ผ่าน)

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: `OK` (1 test)

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py tests/__init__.py requirements.txt
git commit -m "feat: add DC bias calculation for forward-active region"
```

---

### Task 2: Cutoff และ Saturation + warnings

**Files:**
- Modify: `dc_bias.py` (`calculate`)
- Modify: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `DcBiasInput`, `DcBiasResult`, `calculate` จาก Task 1
- Produces: `region` เป็น `"Cutoff"` / `"Saturation"` และ `warnings` ที่มีข้อความภาษาไทย

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

เพิ่มใน `tests/test_dc_bias.py`:
```python
class TestRegionHandling(unittest.TestCase):
    def test_cutoff_when_vth_below_vbe(self):
        r = calculate(DcBiasInput(vcc=12.0, r1=100.0, r2=1.0, rc=2.2, re=1.0, beta=100.0, vbe=0.70))
        self.assertEqual(r.region, "Cutoff")
        self.assertEqual(r.ic_ma, 0.0)
        self.assertEqual(r.ie_ma, 0.0)
        self.assertEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vc, 12.0, places=6)
        self.assertTrue(any("Cutoff" in w for w in r.warnings))

    def test_saturation_when_rc_too_large(self):
        r = calculate(DcBiasInput(vcc=12.0, r1=100.0, r2=22.0, rc=10.0, re=0.1, beta=100.0, vbe=0.70))
        self.assertEqual(r.region, "Saturation")
        self.assertTrue(any("Saturation" in w for w in r.warnings))

    def test_low_beta_still_calculates_with_warning(self):
        r = calculate(DcBiasInput(vcc=12.0, r1=100.0, r2=22.0, rc=2.2, re=1.0, beta=5.0, vbe=0.70))
        self.assertGreater(r.ib_ua, 0.0)
        self.assertTrue(any("β" in w for w in r.warnings))
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL 3 เคสใหม่ (region ยังเป็น Forward Active / ไม่มี warning)

- [ ] **Step 3: เพิ่ม logic ใน `calculate()`**

ลำดับ: คำนวณ VTH/RTH → ถ้า `VTH <= VBE` คืน Cutoff (IB=IC=IE=0, VE=0, VB=VTH, VC=VCC, VCE=VCC)
→ ไม่งั้นคำนวณเต็ม → ถ้า `VCE <= VCE_SAT` หรือ `VCE < 0` ตั้ง region `"Saturation"` + warning
(ระบุ `IC,max ≈ (VCC−VCE_SAT)/(RC+RE)` และว่า `IC = β·IB` ใช้ไม่ได้) → ตรวจ β นอกช่วง 10–1000
เพิ่ม warning → มิฉะนั้น `"Forward Active"`

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: `OK` (4 tests)

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: add cutoff and saturation detection with warnings"
```

---

### Task 3: `parse_inputs` — validation และการแปลงหน่วย

**Files:**
- Modify: `dc_bias.py`
- Modify: `tests/test_dc_bias.py`

**Interfaces:**
- Produces: `FIELDS: tuple[str, ...] = ("vcc","r1","r2","rc","re","beta","vbe")`
  และ `parse_inputs(raw: Mapping[str, str]) -> tuple[DcBiasInput | None, dict[str, str]]`
  (`errors` คีย์เป็นชื่อ field; คืน `(None, errors)` เมื่อมี error, `(inp, {})` เมื่อผ่าน)

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

เพิ่มใน `tests/test_dc_bias.py`:
```python
from dc_bias import FIELDS, parse_inputs

GOOD = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.7"}

class TestParseInputs(unittest.TestCase):
    def test_accepts_valid_strings(self):
        inp, errors = parse_inputs(GOOD)
        self.assertEqual(errors, {})
        self.assertIsNotNone(inp)
        self.assertAlmostEqual(inp.r1, 100.0)

    def test_rejects_non_numeric_and_blank(self):
        raw = dict(GOOD, vcc="abc", r1="")
        inp, errors = parse_inputs(raw)
        self.assertIsNone(inp)
        self.assertIn("vcc", errors)
        self.assertIn("r1", errors)

    def test_rejects_non_finite(self):
        raw = dict(GOOD, rc="nan", re="inf")
        inp, errors = parse_inputs(raw)
        self.assertIsNone(inp)
        self.assertIn("rc", errors)
        self.assertIn("re", errors)

    def test_rejects_non_positive(self):
        raw = dict(GOOD, r1="0", beta="0", vcc="-12")
        inp, errors = parse_inputs(raw)
        self.assertIsNone(inp)
        self.assertEqual(set(errors), {"r1", "beta", "vcc"})
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — `ImportError: cannot import name 'FIELDS'`

- [ ] **Step 3: เพิ่ม `parse_inputs`**

แปลงด้วย `float()` (ตัด whitespace), ปฏิเสธด้วย `math.isfinite` เมื่อไม่ finite,
ตรวจ `vcc > 0`, `r1/r2/rc/re > 0`, `beta > 0`, `vbe > 0`; ข้อความ error ภาษาไทยสั้น ๆ
ต่อ field ("กรุณากรอกตัวเลข" / "ต้องมากกว่า 0")

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: `OK` (8 tests)

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: add input parsing and validation"
```

---

### Task 4: Flask app + หน้าเว็บ (GET /)

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_web.py`

**Interfaces:**
- Consumes: `calculate`, `parse_inputs`, `FIELDS` จาก Task 1–3
- Produces: `app` (Flask instance) และฟังก์ชัน view `index()` / `calculate_route()`
  template context: `form: dict[str,str]`, `errors: dict[str,str]`, `result: DcBiasResult | None`

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

`tests/test_web.py`:
```python
import unittest
from app import app

class TestWeb(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        for name in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{name}"', body)
        self.assertIn("Calculate DC Bias", body)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: สร้าง `app.py`, `templates/index.html`, `static/style.css`**

`app.py`: `app = Flask(__name__)`, `DEFAULTS = {vcc:"12", r1:"100", r2:"22", rc:"2.2", re:"1", beta:"100", vbe:"0.7"}`,
route `GET /` render `index.html` ด้วย `form=DEFAULTS, errors={}, result=None`
template: ฟอร์ม `method="post" action="/calculate"` 7 ช่องพร้อม label มีหน่วย,
ปุ่มข้อความ `Calculate DC Bias`, `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">`,
บล็อกแสดง `errors` และ `result` (ตาราง V/mA/µA + สถานะ + warnings)

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -p "test_web.py" -v`
Expected: `OK` (1 test)

- [ ] **Step 5: Commit**

```bash
git add app.py templates/index.html static/style.css tests/test_web.py
git commit -m "feat: add Flask app with input form"
```

---

### Task 5: POST /calculate — แสดงผลและ error

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`
- Modify: `tests/test_web.py`

**Interfaces:**
- Consumes: ทุกอย่างจาก Task 1–4
- Produces: `POST /calculate` คืน 200 + ผลลัพธ์ หรือ 400 + errors (คงค่าที่กรอก)

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

เพิ่มใน `tests/test_web.py`:
```python
    def test_post_calculate_shows_result(self):
        res = self.client.post("/calculate", data={
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.7"})
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("8.05", body)
        self.assertIn("Forward Active", body)

    def test_post_invalid_shows_error(self):
        res = self.client.post("/calculate", data={
            "vcc": "abc", "r1": "0", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.7"})
        self.assertEqual(res.status_code, 400)
        body = res.get_data(as_text=True)
        self.assertIn("กรุณากรอกตัวเลข", body)
        self.assertNotIn("Traceback", body)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `python -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — 405 Method Not Allowed / 404

- [ ] **Step 3: เพิ่ม route `POST /calculate`**

`raw = {f: request.form.get(f, "") for f in FIELDS}` → `inp, errors = parse_inputs(raw)` →
ถ้า errors: `return render_template("index.html", form=raw, errors=errors, result=None), 400`
→ ไม่ผิด: `result = calculate(inp)` แล้ว render 200

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: `OK` (11 tests)

- [ ] **Step 5: Commit**

```bash
git add app.py templates/index.html tests/test_web.py
git commit -m "feat: handle calculate route with error rendering"
```

---

### Task 6: เอกสาร (README, AGENTS, validation, design-note, reflection)

**Files:**
- Create: `README.md`, `AGENTS.md`, `docs/validation.md`, `docs/design-note.md`, `docs/reflection.md`

**Interfaces:**
- Consumes: ค่าอ้างอิงจาก Global Constraints และผลจริงจาก Task 1–5

- [ ] **Step 1: เขียน `README.md`**

หัวข้อ: ภาพรวม, โครงสร้างไฟล์, วิธีติดตั้ง (`python -m venv .venv`, activate ตาม OS,
`python -m pip install -r requirements.txt`), วิธีรัน (`python -m flask --app app run --debug`,
เปิด `http://127.0.0.1:5000/`), วิธีทดสอบ (`python -m unittest discover -s tests -v`),
ชุดค่าตัวอย่าง + ตารางผลอ้างอิง, ข้อจำกัดของแบบจำลอง (Forward-Active, ไม่ใช่ SPICE)

- [ ] **Step 2: เขียน `docs/validation.md`**

แสดงการคำนวณมือทีละขั้นของชุดอ้างอิง (แทนค่าให้เห็นตัวเลข), ประกาศ `VCE_SAT = 0.20 V`,
ตารางเทียบ "คำนวณมือ" กับ "ผลจากเว็บ" และช่องผลต่าง, ระบุเคส Cutoff/Saturation ที่ทดสอบแล้ว

- [ ] **Step 3: เขียน `AGENTS.md` และ `docs/design-note.md`**

`AGENTS.md`: กติกา — ฟิสิกส์อยู่ใน `dc_bias.py` เท่านั้น, ห้ามแก้ test ให้ผ่านโดยลดความเข้มงวด,
รัน `python -m unittest discover -s tests -v` ก่อน commit ทุกครั้ง, ใช้ kΩ ที่ขอบนอกและ Ω ข้างใน
`design-note.md`: สรุป 1 หน้าจาก spec (approach A, เหตุผล, trade-off)

- [ ] **Step 4: เขียน `docs/reflection.md`**

ตอบ 4 คำถามท้ายใบงาน: (1) ทำไมเปิด `templates/index.html` ตรง ๆ ไม่เท่ากับรัน Flask
(2) ฟอร์มส่งข้อมูลไป Python อย่างไร (3) แก้สมการใน `dc_bias.py` ต้องแก้ HTML ไหม
(4) ทำไมผลนอก region ที่แบบจำลองใช้ไม่ได้ต้องมี warning — ตอบจากสิ่งที่ทำจริงในโปรเจกต์นี้

- [ ] **Step 5: Commit**

```bash
git add README.md AGENTS.md docs/
git commit -m "docs: add README, validation and reflection notes"
```

---

### Task 7: ตรวจรับจริง (venv + server + tests) และเตรียม push

**Files:**
- Modify: `README.md` (ถ้าคำสั่งจริงต่างจากที่เขียน)

- [ ] **Step 1: สร้าง venv และติดตั้ง dependency**

Run: `python -m venv .venv` แล้ว `\.venv\Scripts\python.exe -m pip install -r requirements.txt`
Expected: `Successfully installed Flask-3.1.2 ...`

- [ ] **Step 2: รัน test ทั้งหมดใน venv**

Run: `\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `OK` (11 tests)

- [ ] **Step 3: เปิด server จริงและยิง HTTP request**

Run: `\.venv\Scripts\python.exe -m flask --app app run --port 5000` (background)
แล้ว `Invoke-WebRequest http://127.0.0.1:5000/` และ POST ผ่าน `Invoke-WebRequest -Method Post`
Expected: GET 200 มี `name="vcc"`; POST 200 มี `8.05`; POST ค่าผิดได้ 400
จากนั้นปิด server

- [ ] **Step 4: ตรวจ git status ก่อน commit**

Run: `git status --short` และ `git diff --staged`
Expected: ไม่มี `.venv/`, `__pycache__/`, `.env` ถูก track

- [ ] **Step 5: Commit สุดท้าย + push**

```bash
git add -A
git commit -m "chore: verify app runs locally and tests pass"
git remote add origin https://github.com/<OWNER>/bjt-dc-bias-web-app.git
git push -u origin main
```
Expected: push สำเร็จ (ต้อง sign in GitHub Desktop / มี credential ก่อน)
