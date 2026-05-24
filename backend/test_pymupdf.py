import fitz

doc = fitz.open()
page = doc.new_page()

# A small rectangle
rect = fitz.Rect(100, 100, 150, 120)
page.draw_rect(rect, color=(1,0,0))

# Try to insert long text
text = "This is a very long text that will definitely not fit in this tiny rectangle if the font size is too large."
res = page.insert_textbox(rect, text, fontsize=12, fontname="helv", color=(0,0,0))

print("Return value:", res)

doc.save("test_out.pdf")
doc.close()
