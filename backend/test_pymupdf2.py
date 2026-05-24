import fitz
doc = fitz.open()
page = doc.new_page()
rect = fitz.Rect(100, 100, 150, 120)
page.draw_rect(rect, color=(1,0,0))
text = "This is a very long text that will definitely not fit in this tiny rectangle if the font size is too large."
res = page.insert_textbox(rect, text, fontsize=-1, fontname="helv", color=(0,0,0))
print("Return value with fontsize=-1:", res)
doc.save("test_out2.pdf")
doc.close()
