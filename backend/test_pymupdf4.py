import fitz
doc = fitz.open()
page = doc.new_page()
rect = fitz.Rect(100, 100, 400, 300)
page.draw_rect(rect, color=(1,0,0))
text = "Short text"
res = page.insert_textbox(rect, text, fontsize=-1, fontname="helv", color=(0,0,0))
print("Return value with fontsize=-1 (short text):", res)
doc.save("test_out4.pdf")
doc.close()
