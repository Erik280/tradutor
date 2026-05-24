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

def _draw_text_wrapped(page, rect, text, fontname, fontsize, color):
    """
    Desenha o texto com quebra de linha manual, ignorando a altura do retângulo.
    Garante que o texto sempre será visível, mesmo que transborde o box original.
    """
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


def gerar_pdf_overlay(pdf_bytes: bytes, chunks: List[dict]) -> bytes:
    """
    Recebe o PDF original em bytes e a lista de chunks já traduzidos.
    Retorna o PDF final com o texto traduzido injetado nas coordenadas originais.

    Args:
        pdf_bytes: bytes do PDF original
        chunks: lista de dicts com {numero_pagina, coordenadas, texto_final_revisado, font_size}
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

        for chunk in page_chunks:
            texto = chunk.get("texto_final_revisado") or chunk.get("texto_traduzido_ia", "")
            if not texto:
                continue

            coord = chunk["coordenadas"]
            font_size = chunk.get("font_size") or 10.0
            font_size = max(6.0, min(font_size, 24.0))  # Clamp seguro

            # Re-converter coordenadas bottom-left → top-left (PyMuPDF)
            ph = coord.get("page_height", page_height)
            x0 = coord["x0"]
            y0_tl = ph - coord["y1"]  # topo = altura_pagina - y1 (bottom-left)
            x1 = coord["x1"]
            y1_tl = ph - coord["y0"]  # baixo = altura_pagina - y0 (bottom-left)

            rect = fitz.Rect(x0, y0_tl, x1, y1_tl)

            # 1. Desenhar retângulo branco opaco para cobrir o texto original
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

            # PyMuPDF Base-14 fonts (like Helvetica) only support Latin-1.
            # We must sanitize common Unicode typography to ASCII.
            texto_seguro = texto.replace("\u2013", "-").replace("\u2014", "--")
            texto_seguro = texto_seguro.replace("\u2018", "'").replace("\u2019", "'")
            texto_seguro = texto_seguro.replace("\u201c", '"').replace("\u201d", '"')
            texto_seguro = texto_seguro.replace("\u2026", "...")
            texto_seguro = texto_seguro.encode("latin-1", errors="replace").decode("latin-1")

            # 2. Inserir o texto traduzido na mesma posição
            try:
                rc = page.insert_textbox(
                    rect,
                    texto_seguro,
                    fontsize=font_size,
                    fontname="helv",       # Helvetica (embutida no PyMuPDF)
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT,
                )
                if rc < 0:
                    # Texto não coube no box (muito longo ou box muito apertado).
                    # PyMuPDF não desenhou nada. Usamos fallback manual que ignora altura.
                    _draw_text_wrapped(page, rect, texto_seguro, "helv", font_size, (0, 0, 0))
            except Exception as e:
                logger.warning(f"Falha ao inserir texto na página {page_num}: {e}")
                # Fallback final se algo quebrar bizarramente
                _draw_text_wrapped(page, rect, texto_seguro, "helv", font_size, (0, 0, 0))

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
