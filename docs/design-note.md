# Design Note — BJT DC Bias Web App

สรุปจาก `docs/superpowers/specs/2026-11-10-bjt-dc-bias-webapp-design.md`

## ทางที่เลือก

**Server-rendered form (approach A)**: `POST /calculate` → Flask เรียก `dc_bias.calculate()`
→ render `index.html` กลับมาพร้อมผลลัพธ์ ไม่มี JavaScript

## ทางที่พิจารณาและไม่เลือก

- **JSON API + fetch()** — ยืดหยุ่นกว่าและต่อยอด interactive ได้ใน W5–W7 แต่เพิ่ม JS,
  JSON contract และ tests อีกชั้น เสี่ยงทำไม่ทันในคาบ 3 ชั่วโมง
- **Flask + WTForms + Blueprint** — โครงสร้างระดับ production แต่ไม่มีคะแนน rubric เพิ่ม

## เหตุผล

1. เป้าหมายการเรียนรู้คือ "HTTP request ไปคำนวณที่ Python จริง" ไม่ใช่สถาปัตยกรรมขนาดใหญ่
2. Server-rendered ทำให้ `client.post()` ตรวจ HTML ได้ตรง ๆ — test ง่ายและเร็ว
3. ไม่มี JS แปลว่าอะไรที่เห็นบนหน้าจอมาจาก backend ทั้งหมด (ตรวจสอบได้ด้วย view-source)

## การตัดสินใจสำคัญ

| เรื่อง | ตัดสิน | เหตุผล |
|--------|--------|--------|
| หน่วย R | รับ kΩ, แปลงเป็น Ω จุดเดียวใน `dc_bias.py` | ตรงกับค่าตัวอย่างในใบงานและภาพ preview |
| Route | `GET /` + `POST /calculate` | แยกหน้าที่ชัด, test ง่าย |
| Status code | 200 สำเร็จ / 400 ข้อมูลผิด (ยัง render หน้าเดิม) | ตรงตาม HTTP semantics และยังแสดง error ให้ผู้ใช้เห็น |
| Cutoff | `VTH ≤ VBE` → IB = IC = IE = 0 | ป้องกัน IB ติดลบจากสมการ Forward-Active |
| Saturation | `VCE ≤ 0.20 V` หรือ `VCE < 0` | ประกาศเกณฑ์ชัดใน `docs/validation.md` |
| Tests | `unittest` (stdlib) | ไม่เพิ่ม dependency, ตรงกับคำสั่งในใบงาน |

## สิ่งที่ไม่ทำในรุ่นนี้

AC analysis, Bode plot, transient, load line, bias ชนิดอื่น, ฐานข้อมูล, deployment
— อยู่ใน roadmap W3–W7 ของรายวิชา
