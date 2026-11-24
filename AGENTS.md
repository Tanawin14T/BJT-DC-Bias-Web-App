# AGENTS.md — กติกาสำหรับ AI agent ใน repo นี้

## สถาปัตยกรรม

- สมการฟิสิกส์และ validation ทั้งหมดอยู่ใน `dc_bias.py` เท่านั้น
  ห้าม import Flask/HTML ในโมดูลนี้ และห้ามคำนวณใน `templates/index.html`
- `app.py` ทำหน้าที่ HTTP: อ่าน `request.form`, เรียก `parse_inputs`/`calculate`,
  เลือก status code, render template
- `templates/index.html` แสดงผลเท่านั้น — ห้ามมีตัวเลขผลลัพธ์แบบ hardcode
- `spice_engine.py` เป็น adapter เดียวของ ngspice (Lab 04): validate → สร้าง netlist →
  `subprocess.run` → อ่าน `run.raw` ต้องใช้ argument เป็น list, ไม่ `shell=True`,
  มี `timeout`, แยก temp dir ต่อรัน และคืน error เมื่อ engine/run/output ไม่พร้อม
  (ห้ามคืนผลสำเร็จหรือกราฟเก่าในเส้นทาง error)
- `plots.py` แปลงข้อมูลที่ parse แล้วเป็น SVG พร้อมแกนและหน่วย — browser/app.py
  ห้ามคำนวณแกนฟิสิกส์ใหม่หรือใส่จุดกราฟเอง
- ผล SPICE กับผล Analytical (`dc_bias.py`) ต้องแยกป้ายที่มาชัดเจน ไม่บังคับให้ตัวเลขเท่ากัน
  เพราะสมมติฐานโมเดลต่างกัน

## หน่วย

- อินพุตตัวต้านทานเป็น **kΩ** ที่ขอบนอก (ฟอร์ม, label, test)
- แปลงเป็น **Ω** ด้วย `KOHM_TO_OHM` ภายใน `dc_bias.py` จุดเดียว
- ผลลัพธ์แสดง V, mA, µA, kΩ ตามที่ template กำหนด
- อินพุต simulator: R เป็น kΩ, C เป็น µF, source amplitude เป็น V peak,
  frequency/fstart/fstop เป็น Hz, stop time เป็น ms — แปลงหน่วยใน `spice_engine.py`
  ก่อนเขียน netlist (`s`, `u` ตามสัญลักษณ์ SPICE)

## การทดสอบ

- รัน `python -m unittest discover -s tests -v` ก่อน commit ทุกครั้ง
- ห้ามแก้ test ให้ผ่านโดยลดความเข้มงวด (เช่น ลด `places`, ลบ assertion,
  เปลี่ยนค่าอ้างอิง) — ถ้าผลเปลี่ยนเพราะฟิสิกส์เปลี่ยน ให้แก้ `docs/validation.md`
  และค่าอ้างอิงพร้อมกันอย่างมีเหตุผล
- test ใหม่ต้องเห็น fail ก่อนเขียน implementation
- test ของ adapter ต้องรันได้โดยไม่มี ngspice (ใช้ raw สังเคราะห์ + mock subprocess)
  และห้ามอ้างว่าผลสังเคราะห์เป็นผลจำลองจริง — สถานะ NOT RUN ต้องถูกบันทึกใน
  `docs/validation.md` เมื่อไม่ได้รัน engine จริง

## Git

- commit สั้น ๆ ต่อหนึ่งงาน: `feat:`, `fix:`, `test:`, `docs:`, `chore:`
- ห้าม commit `.venv/`, `__pycache__/`, `.env` (มี `.gitignore` แล้ว)
- ก่อน push ตรวจ `git status` และ `git diff --staged`

## ข้อจำกัดที่ห้ามละเมิด

- ไม่เพิ่ม dependency นอกเหนือจาก Flask โดยไม่ถามเจ้าของ repo
- Flask debug server ใช้เฉพาะ localhost (`127.0.0.1`) ห้ามผูก `0.0.0.0`
- ถ้าผลออกนอก Forward Active ต้องมี warning เสมอ
