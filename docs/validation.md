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
| Python / Flask | 3.14.2 / 3.1.2 (`requirements.txt`) |
| ngspice | **ngspice-47 console** (`ngspice_con.exe`) ติดตั้งจาก SourceForge `ngspice-47_64.7z` ไปที่ `C:\Users\B6808778\AppData\Local\ngspice-47\Spice64\bin\`; ตั้ง `NGSPICE_PATH` ระดับผู้ใช้แล้ว restart Flask `--host 127.0.0.1 --port 5000` ตามกติกา `AGENTS.md` |
| Playwright MCP | **NOT RUN** — ไม่มี tool ที่ชื่อ playwright ปรากฏใน OpenCode (`search` คืน 0 รายการ; เฉพาะ OpenCode Browser Tool ที่มีอยู่) จึงใช้ **OpenCode Browser Tool** ตรวจแทนและ **ไม่นำผลนี้ไปอ้างว่าเป็น Playwright MCP** |
| BJT model | `QCE_GENERIC` = `NPN(IS=1E-14 BF=200 VAF=100 RB=10 CJC=3.5P CJE=8P TF=400P)` คงที่ใน `spice_engine.py` (generic ไม่ได้อ้างรุ่นทรานซิสเตอร์จริง) |
| Vin / Vout reference | `vb` (ฐานหลัง C_in) / `out` (หลัง C_out บน R_L) |

มี 8 แท็บเปิดเรียง B1→B8 ไว้ใน browser แล้ว (แต่ละแท็บค้างผลรันของ case นั้น)

## ผลทดสอบอัตโนมัติ

```
python -m unittest discover -s tests
→ Ran 39 tests ... OK
```

13 tests เดิม + 26 tests ของ adapter/web รวมถึง raw จริงของ ngspice-47
(ค่าต่อบรรทัด), `.tran TSTEP TSTOP`, และ gain ที่หัก DC offset ออก

## ตาราง B1–B8 (OpenCode Browser Tool, หน้า Flask จริง)

| Case | Action ใน browser | Input | ผลที่อ่านจริง | หลักฐาน | Status |
|------|-------------------|-------|---------------|---------|--------|
| B1 | เปิด Fixed/Emitter/Divider แล้ว submit `/calculate` | 12 V, β=100, RB=1000 kΩ / R1=100, R2=22, RC=2.2, RE=1 kΩ | Fixed IC **1.130 mA** VCE **9.514 V**; Emitter **1.026 mA / 8.705 V**; Divider **1.230 mA / 8.052 V** — ตรงค่าอ้างอิง A1–A3 และสลับโหมดได้ | [`b1`](screenshots/lab04-b1-regression.png) (divider) + อ่านข้อความหลัง submit จริงทุกโหมด | **PASS** |
| B2 | เลือก DC แล้วกด Run Simulation | reference fixture, RE=1 kΩ | Engine `ngspice_con.exe` · Status `success` · Model `QCE_GENERIC`; VB **2.048 V**, VE **1.386 V**, VC **8.965 V**, VCE **7.580 V**, IC **1.379 mA** (อ่านจาก `run.raw`) | [`b2`](screenshots/lab04-b2-dc-spice.png) + แผง NETLIST/run.log ในหน้า | **PASS** |
| B3 | เปลี่ยน RE เดียว แล้ว run ซ้ำ | RE 1 → 2 kΩ | VCE **7.580 → 8.944 V**, IC **1.379 → 0.726 mA**, VB **2.048 → 2.103 V** — ผลเปลี่ยนจริง ไม่ใช่ค่าค้าง | [`b3`](screenshots/lab04-b3-change-re.png) เทียบกับ B2 | **PASS** |
| B4 | Run AC ดู Bode | sweep 10 Hz–1 MHz, 100 pts | แกน `Frequency (Hz)`, `Gain (dB)·Vout/Vin`, `Phase (deg)`; จุดแรก `1.000e+01 1.75 -172.6`; Gain สูงสุด **1.76 @ 1.000e+04 Hz**; f3dB `not determined in sweep range` | [`b4`](screenshots/lab04-b4-ac-bode.png) + ตาราง AC samples | **PASS** |
| B5 | Run `.tran` | 10 mV peak, 1 kHz, 5 ms | แกน `Time (ms)` / `Voltage (V)`; Vin AC **0.01 V**, Vout AC **0.0176 V**, gain **1.76**, `กลับเฟส (~180°)` (covariance) | [`b5`](screenshots/lab04-b5-transient.png) | **PASS** |
| B6 | เปลี่ยน source แล้ว run ซ้ำ | 20 mV peak, 2 kHz | Vin AC **0.0199 V**, Vout AC **0.0351 V** — waveform/ค่าจากรันใหม่ ไม่ใช่กราฟ hard-code; gain ยัง ~1.76 | [`b6`](screenshots/lab04-b6-change-source.png) เทียบ B5 | **PASS** |
| B7 | ใส่ RE=0 แล้ว submit | `sim_re = 0` | เห็น `ข้อมูลไม่ถูกต้อง sim_re: ต้องมากกว่า 0`, HTTP 400, **ไม่มี** `#sim-results` | [`b7`](screenshots/lab04-b7-invalid.png) | **PASS** |
| B8 | เปิด desktop + สลับโหมด | viewport ~1280 px | ฟอร์ม Lab 03, `#simulator`, ปุ่ม `Run Simulation`, หน่วย/กราฟอ่านได้ ไม่ตัด; สลับไป fixed สำเร็จ | [`b8`](screenshots/lab04-b8-ui-desktop.png) | **PASS** (desktop) |
| B8 | Mobile viewport ~390 px | — | ควรตรวจกราฟ/ปุ่มบนจอเล็ก | Browser Tool ไม่มีคำสั่งปรับ viewport/device emulation → **NOT RUN** (mobile) | ใช้ CSS `@media (max-width:560px)` แทน; ยังไม่มีหลักฐานจอเล็ก | **NOT RUN** |
| Playwright MCP | ทุก case ตามใบงาน Lab 3 | — | ต้องเห็น tool ก่อนเริ่ม | ไม่พบ Playwright MCP ใน session นี้ → ใช้ OpenCode Browser Tool แทนตามเงื่อนไขที่อนุญาต | — | **NOT RUN** |

## หมายเหตุความถูกต้อง

- ผลทั้งหมดอ่านจาก `run.raw` ที่ ngspice-47 เขียนในรันนั้น; หน้าเว็บแสดง `#sim-results`
  เฉพาะเมื่อ `SimulationResult.ok == True` และมี engine/status/model กำกับเสมอ
- แก้ไขระหว่างตรวจจริง: parser รองรับ raw แบบค่าต่อบรรทัดของ ngspice-47;
  `.tran` ใช้ลำดับ `TSTEP TSTOP` (เดิมสลับ → ได้แค่ 25 µs); AC amplitude หัก DC
  ก่อนหา gain (vb มี DC ~2 V) และ step ละเอียดพอสำหรับ 1 kHz
- `subprocess.run` ใช้ argument เป็น **list**, ไม่มี `shell=True`, มี `timeout`,
  แยก `TemporaryDirectory` ต่อรัน; ชื่อโมเดลถูกจำกัดด้วย regex → ไม่มี injection
- f3dB แสดงข้อความ `not determined in sweep range` เมื่อไม่มีจุด −3 dB ในช่วง sweep
  (ไม่สร้างตัวเลขขึ้นเอง)
- หลักฐานก่อนติดตั้ง engine (error path ตอนไม่มี ngspice) อยู่ที่
  [`lab04-engine-error-desktop.png`](screenshots/lab04-engine-error-desktop.png) —
  ใช้ยืนยันว่าไม่เคยโชว์ผลปลอมในเส้นทาง error

