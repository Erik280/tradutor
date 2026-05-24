import fitz
doc = fitz.open()
page = doc.new_page()
rect = fitz.Rect(100, 100, 150, 120)

text = "This is a very long text that will definitely not fit in this tiny rectangle if the font size is too large."
original_font_size = 12

current_font_size = original_font_size
rc = -1

while rc < 0 and current_font_size >= 4:
    rc = page.insert_textbox(rect, text, fontsize=current_font_size, fontname="helv", color=(0,0,0))
    if rc < 0:
        current_font_size -= 1

print(f"Final font size: {current_font_size}, rc: {rc}")
doc.save("test_out3.pdf")
doc.close()
