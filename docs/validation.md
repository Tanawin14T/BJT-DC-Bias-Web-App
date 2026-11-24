# การตรวจสอบผล (Validation)

เอกสารนี้เป็น **การคำนวณมืออิสระ** ที่ใช้ตรวจผลจากเว็บ ไม่ได้ดึงค่าจากโปรแกรม
ทุกขั้นแสดงการแทนค่า เพื่อให้ตรวจย้อนได้

## สมมติฐาน

- วงจร NPN Common-Emitter, Voltage-Divider Bias
- Forward-Active approximation: V<sub>BE</sub> คงที่ = 0.70 V, β คงที่ = 100
- ไม่คิด Early effect, leakage, ความต้านทานฐาน การเปลี่ยนแปลงตามอุณหภูมิ
- **เกณฑ์ Saturation ที่ประกาศไว้: V<sub>CE,sat</sub> = 0.20 V** (ใบงานไม่ได้ระบุตัวเลข
  จึงกำหนดเองและใช้ค่านี้ตลอดทั้งโปรแกรมใน `dc_bias.py: VCE_SAT`)
- **ช่วง V<sub>BE</sub> ที่ถือว่าอยู่ในแบบจำลอง: 0.5–0.9 V** — นอกช่วงนี้โปรแกรมยังคำนวณให้
  แต่จะแสดง warning เพราะรอยต่อ base-emitter ของ BJT ซิลิคอนจริงไม่ทำงานที่ค่าเหล่านั้น

## อินพุตที่ใช้ตรวจ

VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

## ขั้นที่ 1 — Thevenin equivalent ที่ฐาน

```
VTH = VCC · R2 / (R1 + R2)
    = 12 × 22 / (100 + 22)
    = 264 / 122
    = 2.1639 V

RTH = R1 · R2 / (R1 + R2)
    = 100 × 22 / 122
    = 18.0328 kΩ
```

## ขั้นที่ 2 — กระแสเบส

```
IB = (VTH − VBE) / (RTH + (β + 1)·RE)
   = (2.1639 − 0.70) / (18.0328 + 101 × 1)
   = 1.4639 / 119.0328 mA   [V / kΩ = mA]
   = 0.0122987 mA
   = 12.299 µA
```

## ขั้นที่ 3 — กระแสและแรงดันที่เหลือ

```
IC = β · IB          = 100 × 12.299 µA = 1.2299 mA
IE = (β + 1) · IB    = 101 × 12.299 µA = 1.2422 mA

VE = IE · RE         = 1.2422 mA × 1 kΩ  = 1.2422 V
VB = VE + VBE        = 1.2422 + 0.70     = 1.9422 V
VC = VCC − IC · RC   = 12 − 1.2299 × 2.2 = 12 − 2.7057 = 9.2943 V
VCE = VC − VE        = 9.2943 − 1.2422   = 8.0522 V
```

## ขั้นที่ 4 — ตรวจสอบโหมดการทำงาน

- `VTH = 2.1639 V > VBE = 0.70 V` → มีกระแสเบสไหล (ไม่ใช่ Cutoff)
- `VCE = 8.0522 V > VCE,sat = 0.20 V` → อยู่ใน Forward Active
- กำลังที่ทรานซิสเตอร์: `P = VCE · IC ≈ 8.05 × 1.23 = 9.9 mW` (ไม่เกินอุปกรณ์ TO-92 ทั่วไป)

## ตารางเทียบ "คำนวณมือ" กับ "ผลจากเว็บ"

| ปริมาณ | คำนวณมือ | ผลจากเว็บ | ผลต่าง |
|--------|----------|-----------|--------|
| VTH [V] | 2.1639 | 2.164 | < 0.001 |
| RTH [kΩ] | 18.0328 | 18.033 | < 0.001 |
| IB [µA] | 12.299 | 12.30 | < 0.01 |
| IC [mA] | 1.2299 | 1.230 | < 0.001 |
| IE [mA] | 1.2422 | 1.242 | < 0.001 |
| VE [V] | 1.2422 | 1.242 | < 0.001 |
| VB [V] | 1.9422 | 1.942 | < 0.001 |
| VC [V] | 9.2943 | 9.294 | < 0.001 |
| VCE [V] | 8.0522 | 8.052 | < 0.001 |
| Region | Forward Active | Forward Active | ตรงกัน |

ผลต่างทั้งหมดอยู่ในระดับการปัดเศษที่หน้าจอแสดง (3 ตำแหน่ง) ไม่ใช่ความคลาดเคลื่อนของสมการ

## เคสนอกช่วง Forward Active ที่ทดสอบแล้ว

### Cutoff — R1 = 100 kΩ, R2 = 1 kΩ

```
VTH = 12 × 1 / 101 = 0.1188 V  <  VBE = 0.70 V
```

ไม่มีกระแสเบส → IB = IC = IE = 0, VE = 0, VC = VCC = 12 V, VB = VTH = 0.119 V
เว็บรายงาน **Cutoff** พร้อมคำเตือน (ตรวจโดย `test_cutoff_when_vth_below_vbe`)

### Saturation — RC = 10 kΩ, RE = 0.1 kΩ

```
IB = 1.4639 / (18.0328 + 10.1) = 52.04 µA
IC = 100 × 52.04 µA            = 5.204 mA
VC = 12 − 5.204 × 10           = −40.04 V   (ติดลบ → เป็นไปไม่ได้)
```

สมการ Forward-Active ให้ V<sub>C</sub> ติดลบ แปลว่าวงจรถูกจำกัดด้วย RC/RE ไม่ใช่ด้วย β
ขอบเขตกระแสจริงคือ

```
IC,max ≈ (VCC − VCE,sat) / (RC + RE) = (12 − 0.2) / 10.1 = 1.168 mA
```

เว็บรายงาน **Saturation** พร้อมคำเตือนว่า `IC = β·IB` ใช้ไม่ได้
(ตรวจโดย `test_saturation_when_rc_too_large`)

## Lab 03 — วงจรใหม่ (คำนวณมืออิสระ)

ใช้ร่วมกัน: VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V

**Fixed Bias · RB = 1000 kΩ** (VE = 0 V)

```
IB = (12 − 0.70)/1 MΩ = 11.3 µA
IC = 100 × 11.3 µA = 1.130 mA
VC = 12 − 1.130 × 2.2 = 9.514 V → VCE = 9.514 V
```

**Emitter Bias · RB = 1000 kΩ, RE = 1 kΩ**

```
IB = 11.3 V / (1000 + 101×1) kΩ = 10.2634 µA
IC = 1.02634 mA · IE = 1.03660 mA · VE = 1.03660 V
VC = 12 − 1.02634×2.2 = 9.74205 V → VCE = 8.70545 V
```

**Emitter Bias · RB = 1000 kΩ, RE = 2 kΩ** (A4: RE เพิ่ม → IC ลด)

```
IB = 11.3 / (1000 + 101×2) = 9.400998 µA
IC = 0.940100 mA · VE = 1.89900 V · VCE = 9.93178 − 1.89900 = 8.03278 V
```

### ผลที่อ่านจากเบราว์เซอร์จริง (OpenCode Browser)

| กรณี | โหมด / ค่า | คาดหมาย (มือ) | เห็นจริง | สถานะ |
|------|-----------|---------------|----------|--------|
| A1 | Divider · R1=100, R2=22, RE=1 | IC 1.230 mA · VCE 8.052 V | IC 1.230 mA · VCE 8.052 V | PASS |
| A2 | Fixed · RB=1000 | IC 1.130 mA · VCE 9.514 V | IC 1.130 mA · VCE 9.514 V | PASS |
| A3 | Emitter · RB=1000, RE=1 | IC 1.026 mA · VCE 8.705 V | IC 1.026 mA · VCE 8.705 V | PASS |
| A4 | Emitter · RB=1000, RE=2 | IC 0.940 mA · VCE 8.033 V | IC 0.940 mA · VCE 8.033 V | PASS |
| A5 | Fixed · RB=0 | แจ้งแก้ RB ไม่แสดงผลเก่า | 「ต้องมากกว่า 0」 ไม่มีตารางผล | PASS |

โหมด Divider ใช้ตัวแปลงหน่วยเดียวกัน (`KOHM_TO_OHM`) และผลเท่าเดิม ฟังก์ชันใหม่
`calculate_fixed` / `calculate_emitter` อยู่ใน `dc_bias.py` ส่วน `app.py` เลือกตาม `mode`

## สรุป

- ค่าอ้างอิงใน `README.md`, `tests/test_dc_bias.py` และผลบนหน้าจอตรงกับการคำนวณมือชุดเดียวกัน
- โปรแกรม **ไม่ตรวจ** ความถูกต้องทางกายภาพของค่าอุปกรณ์ (เช่น กำลัง dissipate จริง
  หรือพิกัดของทรานซิสเตอร์) — เป็นหน้าที่ผู้ออกแบบ

---

# Lab 04 — CE Amplifier Simulator (ngspice)

## สภาพแวดล้อมที่ใช้ตรวจ

| รายการ | ค่าที่พบจริง |
|--------|-------------|
| Python | 3.14.2 |
| Flask | 3.1.2 (จาก `requirements.txt`) |
| ngspice version | **ไม่มี executable ในเครื่องนี้** (`where ngspice` ไม่พบ) → ผลจำลองจริง **NOT RUN** |
| BJT model | `QCE_GENERIC` = `NPN(IS=1E-14 BF=200 VAF=100 RB=10 CJC=3.5P CJE=8P TF=400P)` ตั้งค่าคงที่ใน `spice_engine.py` (generic ไม่ได้อ้างรุ่นจริง) |
| Vin reference | วัดที่ node `vb` (ฐาน หลัง C_in) |
| Vout reference | วัดที่ node `out` (หลัง C_out บน R_L) |

การตรวจ adapter ใช้ raw file สังเคราะห์ใน `tests/test_spice_engine.py` เท่านั้น
**ไม่ได้นำตัวเลขจาก raw สังเคราะห์ไปแสดงว่าเป็นผล ngspice จริง** บนหน้าเว็บ

## ผลทดสอบอัตโนมัติ

```
python -m unittest discover -s tests -v
→ Ran 35 tests ... OK
```

แบ่งเป็น 13 tests เดิม (Lab 2/3) + 22 tests ใหม่ (netlist, validation, raw parser,
engine missing, nonzero exit, empty raw, timeout, subprocess argument shape,
HTTP success/error/invalid ของ `/simulate`)

## ตาราง B1–B8 (ตรวจจาก browser จริงเท่าที่เครื่องรองรับ)

| Case | Method | Input | Expected / Reference | Observed | Evidence | Status |
|------|--------|-------|----------------------|----------|----------|--------|
| B1 | OpenCode browser, submit `form.bias-form` | Divider 12 V / 100 / 22 / 2.2 / 1 kΩ, β=100 | IC 1.230 mA · VCE 8.052 V · Forward Active | พบข้อความ `8.052` และ `Forward Active` บนหน้าเว็บ | `browser.find` หลัง submit จริง | **PASS** |
| B2 | Run DC `.op` กับ ngspice จริง | reference fixture | VB/VE/VC/VCE/IC จาก log/raw จริง | ไม่ได้รัน เพราะไม่มี ngspice | — | **NOT RUN** |
| B3 | เปลี่ยน RE แล้วรันซ้ำ | RE อื่น | Operating point เปลี่ยน | ไม่มี engine ให้รัน; มี unit test ตรวจ RE=0 ถูกปฏิเสธและ netlist ใช้ค่าที่ตรวจแล้ว | `test_rejects_zero_emitter_resistor`, `test_dc_uses_op...` | **NOT RUN** (real run) |
| B4 | Run AC + look at Bode | 10 mV / 1 kHz, sweep 10 Hz–1 MHz | แกน Frequency/Gain(dB)/Phase(deg) มีหน่วยและข้อมูลจริง | ไม่มี raw จริง; parser ถูกทดสอบด้วย complex synthetic raw (gain 10, phase ≈180°) | `test_parse_ac_complex_gain_and_phase` | **NOT RUN** (real run) |
| B5 | Run `.tran` | 10 mV peak, 1 kHz | Vin/Vout vs time, กลับเฟส | ไม่มี raw จริง; parser/summary ทดสอบด้วย synthetic real raw | `test_parse_transient_points` | **NOT RUN** (real run) |
| B6 | เปลี่ยน amplitude/frequency แล้วรันซ้ำ | source ใหม่ | wave เปลี่ยนตาม input | ไม่มี engine ให้รัน; validation ทดสอบ amplitude/frequency ผิดแล้วถูกปฏิเสธ | `test_rejects_bad_source_values` | **NOT RUN** (real run) |
| B7 | Browser submit ฟอร์ม simulator | `sim_re = 0` | แจ้ง error ไม่ค้าง ไม่โชว์ผลสำเร็จ | เห็น `sim_re: ต้องมากกว่า 0` และไม่มี `#sim-results` | `browser.find` หลัง submit จริง | **PASS** |
| B7b | Browser submit ค่าถูกแต่ไม่มี engine | RE กลับเป็น 1 kΩ | แจ้ง error ไม่ส่งผลปลอม | เห็น `Simulation failed` · `ไม่พบ ngspice — ตรวจ PATH หรือตั้งค่า NGSPICE_PATH แล้วลองใหม่` ไม่มี `#sim-results` | `browser.find` + [`screenshot`](screenshots/lab04-engine-error-desktop.png) | **PASS** |
| B8 | Desktop viewport ~1280 px | เปิดหน้าเว็บ + เปลี่ยนโหมด | ปุ่ม/ฟอร์ม/ข้อความอ่านได้ ไม่ตัด | ฟอร์ม Lab 03 และ `#simulator` แสดงครบ, button `Run Simulation` เห็นชัด | screenshot ด้านบน | **PASS** (desktop) |
| B8 | Mobile viewport ~390 px | — | กราฟ/หน่วย/ปุ่มอ่านง่าย | เครื่องนี้ไม่มี tool ปรับ viewport → ไม่ได้ตรวจ | — | **NOT RUN** (mobile) |

## หมายเหตุความถูกต้อง

- หน้าเว็บจะแสดง `#sim-results` เฉพาะเมื่อ `SimulationResult.ok == True` ซึ่งเกิดขึ้น
  หลังอ่าน `run.raw` ที่มีข้อมูลจริงเท่านั้น; ทุกเส้นทาง error คืน status 400/503
  และไม่มีตารางผล/กราฟเก่า
- `subprocess.run` ได้ argument เป็น **list**, ไม่มี `shell=True`, มี `timeout=30`
  และแยก `TemporaryDirectory` ต่อหนึ่งรัน (ตรวจโดย `test_subprocess_is_list_no_shell_with_timeout`)
- ฟอร์มตรวจตัวเลข/finite/ช่วงก่อนสร้าง netlist ชื่อโมเดลถูกจำกัดด้วย regex
  (ตรวจ `test_rejects_injection_into_model_name`) → ข้อความจากฟอร์มไม่ต่อเข้า command
- เมื่อติดตั้ง ngspice แล้ว ให้รัน `python -m flask --app app run`,
  เปิด <http://127.0.0.1:5000/> กด **Run Simulation** ในแต่ละโหมด แล้วอัปเดต
  B2–B6 จาก log/raw จริงก่อนส่งงาน — ตัวเลข gain/cutoff ต้องมาจากรันนั้น
- f3dB จะแสดงข้อความ `not determined in sweep range` ถ้าไม่มีจุด −3 dB ในช่วง sweep
  (ไม่สร้างตัวเลขขึ้นเอง)
