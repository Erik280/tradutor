import fitz

def _draw_text_wrapped(page, rect, text, fontname, original_fontsize, color):
    fontsize = original_fontsize
    min_fontsize = 6.0
    
    lines_to_draw = []
    
    while fontsize >= min_fontsize:
        lines_to_draw = []
        overflows_width = False
        
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                lines_to_draw.append("")
                continue
                
            current_line = []
            for word in words:
                test_line = " ".join(current_line + [word])
                w = fitz.get_text_length(test_line, fontname=fontname, fontsize=fontsize)
                if w > rect.width:
                    if not current_line:
                        # Palavra muito grande
                        overflows_width = True
                        break
                    lines_to_draw.append(" ".join(current_line))
                    current_line = [word]
                else:
                    current_line.append(word)
            
            if overflows_width:
                break
                
            if current_line:
                lines_to_draw.append(" ".join(current_line))
                
        if overflows_width:
            fontsize -= 0.5
            continue
            
        total_height = len(lines_to_draw) * fontsize * 1.2
        if total_height <= rect.height:
            break
            
        fontsize -= 0.5
        
    # Se ainda assim não couber (ou palavra gigante), garante que temos as linhas calculadas na menor fonte
    if not lines_to_draw:
        # Força o cálculo com o fontsize final
        lines_to_draw = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                lines_to_draw.append("")
                continue
            current_line = []
            for word in words:
                test_line = " ".join(current_line + [word])
                w = fitz.get_text_length(test_line, fontname=fontname, fontsize=fontsize)
                if w > rect.width and current_line:
                    lines_to_draw.append(" ".join(current_line))
                    current_line = [word]
                else:
                    current_line.append(word)
            if current_line:
                lines_to_draw.append(" ".join(current_line))

    # Desenha o texto
    y = rect.y0 + fontsize
    for line in lines_to_draw:
        if line:
            page.insert_text((rect.x0, y), line, fontsize=fontsize, fontname=fontname, color=color)
        y += fontsize * 1.2


doc = fitz.open()
page = doc.new_page()

# Very small rectangle
rect = fitz.Rect(100, 100, 200, 120)
page.draw_rect(rect, color=(1,0,0))
text = "Velocidade do RPM"
_draw_text_wrapped(page, rect, text, "helv", 14.0, (0,0,0))

doc.save("test_out8.pdf")
doc.close()
