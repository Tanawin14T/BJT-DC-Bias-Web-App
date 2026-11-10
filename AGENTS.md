# AGENTS.md — กติกาสำหรับ AI agent ใน repo นี้

## สถาปัตยกรรม

- สมการฟิสิกส์และ validation ทั้งหมดอยู่ใน `dc_bias.py` เท่านั้น
  ห้าม import Flask/HTML ในโมดูลนี้ และห้ามคำนวณใน `templates/index.html`
- `app.py` ทำหน้าที่ HTTP: อ่าน `request.form`, เรียก `parse_inputs`/`calculate`,
  เลือก status code, render template
- `templates/index.html` แสดงผลเท่านั้น — ห้ามมีตัวเลขผลลัพธ์แบบ hardcode

## หน่วย

- อินพุตตัวต้านทานเป็น **kΩ** ที่ขอบนอก (ฟอร์ม, label, test)
- แปลงเป็น **Ω** ด้วย `KOHM_TO_OHM` ภายใน `dc_bias.py` จุดเดียว
- ผลลัพธ์แสดง V, mA, µA, kΩ ตามที่ template กำหนด

## การทดสอบ

- รัน `python -m unittest discover -s tests -v` ก่อน commit ทุกครั้ง
- ห้ามแก้ test ให้ผ่านโดยลดความเข้มงวด (เช่น ลด `places`, ลบ assertion,
  เปลี่ยนค่าอ้างอิง) — ถ้าผลเปลี่ยนเพราะฟิสิกส์เปลี่ยน ให้แก้ `docs/validation.md`
  และค่าอ้างอิงพร้อมกันอย่างมีเหตุผล
- test ใหม่ต้องเห็น fail ก่อนเขียน implementation

## Git

- commit สั้น ๆ ต่อหนึ่งงาน: `feat:`, `fix:`, `test:`, `docs:`, `chore:`
- ห้าม commit `.venv/`, `__pycache__/`, `.env` (มี `.gitignore` แล้ว)
- ก่อน push ตรวจ `git status` และ `git diff --staged`

## ข้อจำกัดที่ห้ามละเมิด

- ไม่เพิ่ม dependency นอกเหนือจาก Flask โดยไม่ถามเจ้าของ repo
- Flask debug server ใช้เฉพาะ localhost (`127.0.0.1`) ห้ามผูก `0.0.0.0`
- ถ้าผลออกนอก Forward Active ต้องมี warning เสมอ
