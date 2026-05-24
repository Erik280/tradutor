import fitz
doc = fitz.open()
page = doc.new_page()
# Tight rect
rect = fitz.Rect(100, 100, 150, 113)
page.draw_rect(rect, color=(1,0,0))
text = "This is a very long text that will not fit."
res = page.insert_textbox(rect, text, fontsize=12, fontname="helv", color=(0,0,0))
if res < 0:
    expanded_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1 + 12 * 5)
    page.draw_rect(expanded_rect, color=(0,1,0), fill=None)
    res2 = page.insert_textbox(expanded_rect, text, fontsize=12, fontname="helv", color=(0,0,0))
    print("Expanded res:", res2)

doc.save("test_out6.pdf")
doc.close()
