import fitz
doc = fitz.open()
page = doc.new_page()
# font_size = 12, line height = 14.4
# rect height = 13 (less than line height)
rect = fitz.Rect(100, 100, 300, 113)
page.draw_rect(rect, color=(1,0,0))
text = "This is a single line text."
res = page.insert_textbox(rect, text, fontsize=12, fontname="helv", color=(0,0,0))
print("Return value with tight height:", res)
doc.save("test_out5.pdf")
doc.close()
