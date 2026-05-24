import fitz

def draw_text_wrapped(page, rect, text, fontname, fontsize, color):
    y = rect.y0 + fontsize
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            y += fontsize * 1.2
            continue
            
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            w = fitz.get_text_length(test_line, fontname=fontname, fontsize=fontsize)
            if w > rect.width and current_line:
                page.insert_text((rect.x0, y), " ".join(current_line), fontsize=fontsize, fontname=fontname, color=color)
                y += fontsize * 1.2
                current_line = [word]
            else:
                current_line.append(word)
        
        if current_line:
            page.insert_text((rect.x0, y), " ".join(current_line), fontsize=fontsize, fontname=fontname, color=color)
            y += fontsize * 1.2

doc = fitz.open()
page = doc.new_page()
rect = fitz.Rect(100, 100, 150, 113)
page.draw_rect(rect, color=(1,0,0))
text = "This is a very long text that will not fit in the box because it is very long and has words like definitely."
draw_text_wrapped(page, rect, text, "helv", 12, (0,0,0))

doc.save("test_out7.pdf")
doc.close()
