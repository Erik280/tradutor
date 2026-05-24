"""
export_service.py — Motor de Exportação

Modo 1: PDF Overlay (com imagens)
  - Abre o PDF original (diagramas CAD intactos)
  - Cobre texto antigo com retângulo opaco
  - Injeta texto_final_revisado nas coordenadas exatas
  - Resultado: PDF 100% selecionável e pesquisável

Modo 2: Markdown (sem imagens)
  - Concatena texto_final_revisado ordenado por página/chunk
  - Gera arquivo .md estruturado com separadores de seção
"""

import io
import logging
from typing import List

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# ─── MODO 1: PDF com Overlay ──────────────────────────────────────────────────

def _draw_text_wrapped(page, rect, text, fontname, original_fontsize, color, quebra_linha_manual=False):
    """
    Desenha o texto com quebra de linha manual.
    Encolhe automaticamente a fonte (até um limite) se o texto quebrado
    não couber na altura do retângulo, evitando invasão de bordas (como em tabelas).
    Se quebra_linha_manual for True, ignora a largura e nunca quebra a linha automaticamente.
    """
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
                
                # Se for quebra manual, nunca transborda a largura (nunca auto-quebra)
                if w > rect.width and not quebra_linha_manual:
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
        
    # Se ainda não couber (ou palavras gigantes), garante que temos as linhas calculadas
    if not lines_to_draw:
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
                if w > rect.width and current_line and not quebra_linha_manual:
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


def gerar_pdf_overlay(pdf_bytes: bytes, chunks: List[dict], quebra_linha_manual: bool = False, font_offset: float = -2.0) -> bytes:
    """
    Recebe o PDF original em bytes e a lista de chunks já traduzidos.
    Retorna o PDF final com o texto traduzido injetado nas coordenadas originais.

    Args:
        pdf_bytes: bytes do PDF original
        chunks: lista de dicts com {numero_pagina, coordenadas, texto_final_revisado, font_size, offset_x, offset_y, custom_font_size}
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Agrupar chunks por página para processar eficientemente
    chunks_por_pagina: dict[int, List[dict]] = {}
    for c in chunks:
        pg = c["numero_pagina"]
        chunks_por_pagina.setdefault(pg, []).append(c)

    for page_num, page_chunks in chunks_por_pagina.items():
        page = doc[page_num - 1]  # PyMuPDF usa índice 0-based
        page_height = page.rect.height

        # PASS 1: Desenhar todos os retângulos brancos primeiro (mantém coordenadas originais para cobrir o texto).
        for chunk in page_chunks:
            coord = chunk["coordenadas"]
            ph = coord.get("page_height", page_height)
            x0 = coord["x0"]
            y0_tl = ph - coord["y1"]
            x1 = coord["x1"]
            y1_tl = ph - coord["y0"]

            rect = fitz.Rect(x0, y0_tl, x1, y1_tl)
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

        # PASS 2: Injetar os textos traduzidos com offsets
        for chunk in page_chunks:
            texto = chunk.get("texto_final_revisado") or chunk.get("texto_traduzido_ia", "")
            if not texto:
                continue

            coord = chunk["coordenadas"]
            
            # Fonte: usa a custom_font_size se existir, senão usa original + font_offset global
            font_size_original = chunk.get("font_size") or 10.0
            custom_font = chunk.get("custom_font_size")
            if custom_font is not None:
                font_size = max(4.0, min(custom_font, 48.0))
            else:
                font_size = max(6.0, min(font_size_original + font_offset, 24.0))

            # Offsets manuais de posição
            ox = chunk.get("offset_x") or 0.0
            oy = chunk.get("offset_y") or 0.0

            ph = coord.get("page_height", page_height)
            x0 = coord["x0"] + ox
            y0_tl = ph - coord["y1"] + oy
            x1 = coord["x1"] + ox
            y1_tl = ph - coord["y0"] + oy
            
            # Garantir que o x1 seja pelo menos maior que x0, mesmo após deslocamento
            if x1 <= x0: x1 = x0 + 10.0
            rect = fitz.Rect(x0, y0_tl, x1, y1_tl)

            texto_seguro = texto.replace("\u2013", "-").replace("\u2014", "--")
            texto_seguro = texto_seguro.replace("\u2018", "'").replace("\u2019", "'")
            texto_seguro = texto_seguro.replace("\u201c", '"').replace("\u201d", '"')
            texto_seguro = texto_seguro.replace("\u2026", "...")
            texto_seguro = texto_seguro.replace("•", "-").replace("·", "-").replace("■", "-").replace("▪", "-").replace("►", "-")
            texto_seguro = texto_seguro.encode("latin-1", errors="replace").decode("latin-1")

            try:
                if quebra_linha_manual:
                    _draw_text_wrapped(page, rect, texto_seguro, "helv", font_size, (0, 0, 0), quebra_linha_manual=True)
                else:
                    rc = page.insert_textbox(
                        rect,
                        texto_seguro,
                        fontsize=font_size,
                        fontname="helv",
                        color=(0, 0, 0),
                        align=fitz.TEXT_ALIGN_LEFT,
                    )
                    if rc < 0:
                        _draw_text_wrapped(page, rect, texto_seguro, "helv", font_size, (0, 0, 0), False)
            except Exception as e:
                logger.warning(f"Falha ao inserir texto na página {page_num}: {e}")
                _draw_text_wrapped(page, rect, texto_seguro, "helv", font_size, (0, 0, 0), False)

    # Serializar para bytes com compressão
    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True, clean=True)
    doc.close()
    return output.getvalue()


# ─── MODO 2: Markdown Limpo ───────────────────────────────────────────────────

def gerar_markdown(chunks: List[dict], nome_documento: str = "Manual") -> bytes:
    """
    Gera um arquivo Markdown estruturado com o texto traduzido ordenado por
    número de página e índice do chunk.

    Returns: bytes do arquivo .md em UTF-8
    """
    linhas = [
        f"# {nome_documento}",
        "",
        "> Documento gerado pelo Tradutor Técnico — TransformaFuturo",
        "",
    ]

    pagina_atual = None

    for chunk in sorted(chunks, key=lambda c: (c["numero_pagina"], c["chunk_index"])):
        pg = chunk["numero_pagina"]
        texto = chunk.get("texto_final_revisado") or chunk.get("texto_traduzido_ia", "")

        if not texto:
            continue

        # Separador de página
        if pg != pagina_atual:
            if pagina_atual is not None:
                linhas.append("\n---\n")
            linhas.append(f"## Página {pg}\n")
            pagina_atual = pg

        # Ajustar o tipo de bloco
        block_type = chunk.get("block_type", "text")

        if block_type == "heading":
            linhas.append(f"### {texto}\n")
        elif block_type in ("list",):
            linhas.append(texto + "\n")
        elif block_type == "table":
            linhas.append(texto + "\n")
        else:
            linhas.append(texto + "\n")

    conteudo = "\n".join(linhas)
    return conteudo.encode("utf-8")
