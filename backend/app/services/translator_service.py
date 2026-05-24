"""
translator_service.py — Núcleo de Tradução

Pipeline assíncrono:
  A) Extração espacial com PyMuPDF
  B) Tradução contextual com LangChain + Glossário da empresa
  C) Persistência de chunks no Supabase
"""

import asyncio
import logging
import uuid
import os
from typing import List

import fitz  # PyMuPDF

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from app.core.supabase_client import get_supabase

logger = logging.getLogger(__name__)


# ─── Constantes de configuração ───────────────────────────────────────────────

CHUNK_BATCH_SIZE  = 10    # Chunks enviados por chamada à LLM
MIN_CHARS_TO_TRANSLATE = 3  # Ignorar blocos muito pequenos (pontos, traços)

SYSTEM_PROMPT_TEMPLATE = """\
Você é um tradutor técnico especialista em engenharia industrial e sistemas CAD/CAM.

REGRAS OBRIGATÓRIAS:
1. Traduza SOMENTE o texto recebido, sem adicionar explicações.
2. Preserve toda formatação Markdown (negritos ****, tabelas |, listas -, headers #).
3. Preserve números, códigos, nomes de peças e referências exatamente como estão.
4. Use OBRIGATORIAMENTE o glossário abaixo para substituição de termos técnicos:
   {glossario}
5. Termos marcados como NÃO TRADUZIR devem ser mantidos no idioma original.
6. Retorne APENAS os textos traduzidos, separados por |||, na mesma ordem dos originais.

GLOSSÁRIO DA EMPRESA:
{glossario}
"""


# ─── ETAPA A: Extração Espacial com PyMuPDF ──────────────────────────────────

def extrair_chunks_do_pdf(pdf_bytes: bytes) -> List[dict]:
    """
    Lê o PDF e extrai todos os blocos de texto com suas coordenadas.
    Retorna lista de dicts compatível com public.chunks_traducao.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks = []
    chunk_global_index = 0

    for page_num, page in enumerate(doc, start=1):
        # Obtém blocos de texto com detalhes de fontes (flags=2 para dict completo)
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        page_height = page.rect.height  # Necessário para converter coord PyMuPDF→PDF

        for block in blocks:
            if block.get("type") != 0:  # 0 = texto, 1 = imagem — ignoramos imagens
                continue

            # Concatenar linhas do bloco
            full_text = ""
            font_name = None
            font_size = None

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    full_text += span.get("text", "")
                    if font_name is None:
                        font_name = span.get("font")
                        font_size = span.get("size")
                full_text += "\n"

            full_text = full_text.strip()
            if len(full_text) < MIN_CHARS_TO_TRANSLATE:
                continue

            # Bounding box — PyMuPDF usa top-left origin, PDF usa bottom-left
            bbox = block["bbox"]  # (x0, y0, x1, y1) em pts, top-left origin
            x0, y0_tl, x1, y1_tl = bbox

            # Converter para bottom-left origin (padrão PDF/ReportLab)
            y0 = page_height - y1_tl
            y1 = page_height - y0_tl

            chunks.append({
                "chunk_index":    chunk_global_index,
                "numero_pagina":  page_num,
                "texto_original": full_text,
                "coordenadas": {
                    "x0": round(x0, 2),
                    "y0": round(y0, 2),
                    "x1": round(x1, 2),
                    "y1": round(y1, 2),
                    "width":  round(x1 - x0, 2),
                    "height": round(y1 - y0, 2),
                    "page_height": round(page_height, 2),
                },
                "font_name":  font_name,
                "font_size":  font_size,
                "block_type": _classify_block(full_text, font_size),
                "status":     "pendente",
            })
            chunk_global_index += 1

    doc.close()
    return chunks


def _classify_block(text: str, font_size: float | None) -> str:
    """Heurística simples para classificar blocos."""
    if font_size and font_size >= 14:
        return "heading"
    if text.startswith("|") or "\t" in text:
        return "table"
    if text.startswith(("- ", "* ", "• ")):
        return "list"
    return "text"


# ─── ETAPA B: Tradução com LangChain + Glossário ─────────────────────────────

def _carregar_glossario(empresa_id: str) -> dict:
    """Busca o glossário da empresa no Supabase."""
    sb = get_supabase()
    res = sb.table("glossario") \
        .select("termo_orig, termo_pt, nao_traduzir") \
        .eq("empresa_id", empresa_id) \
        .execute()

    glossario = {}
    for item in (res.data or []):
        if item["nao_traduzir"]:
            glossario[item["termo_orig"]] = f"[NÃO TRADUZIR: {item['termo_orig']}]"
        else:
            glossario[item["termo_orig"]] = item["termo_pt"]
    return glossario


def _formatar_glossario_para_prompt(glossario: dict) -> str:
    if not glossario:
        return "(nenhum termo específico)"
    linhas = [f'"{orig}" → "{trad}"' for orig, trad in glossario.items()]
    return "\n".join(linhas)


async def _traduzir_lote(
    textos: List[str],
    glossario_str: str,
    llm: ChatOpenAI,
) -> List[str]:
    """Envia um lote de textos para a LLM e retorna as traduções."""
    textos_juntos = "\n|||\n".join(textos)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT_TEMPLATE.format(glossario=glossario_str)),
        HumanMessage(content=textos_juntos),
    ]

    try:
        resposta = await asyncio.to_thread(llm.invoke, messages)
        traduzidos = resposta.content.split("|||")
        # Garantir mesma quantidade de textos retornados
        while len(traduzidos) < len(textos):
            traduzidos.append(textos[len(traduzidos)])  # fallback: original
        return [t.strip() for t in traduzidos[:len(textos)]]
    except Exception as e:
        logger.error(f"Erro na LLM: {e}")
        return textos  # fallback: retorna originais


# ─── PIPELINE PRINCIPAL (chamado como BackgroundTask) ────────────────────────

async def run_translation_pipeline(
    documento_id: str,
    empresa_id: str,
    storage_path: str,
    source_lang: str = "de",
    target_lang: str = "pt",
    model: str = "gpt-4o-mini",
    openai_api_key: str | None = None,
):
    """
    Pipeline completo:
    1. Baixa o PDF do Supabase Storage
    2. Extrai chunks com PyMuPDF
    3. Persiste chunks (status=pendente)
    4. Traduz em lotes com LangChain
    5. Atualiza chunks com as traduções
    6. Atualiza status do documento
    """
    sb = get_supabase()
    logger.info(f"[{documento_id}] Pipeline iniciado. Modelo: {model}")

    try:
        # ── Status: processando ────────────────────────────────────────────────
        sb.table("documents").update({"status": "processing"}) \
            .eq("id", documento_id).execute()

        # ── Etapa A: Download e Extração ───────────────────────────────────────
        logger.info(f"[{documento_id}] Baixando PDF do Storage...")
        pdf_bytes = sb.storage.from_("documents").download(storage_path)

        logger.info(f"[{documento_id}] Extraindo chunks com PyMuPDF...")
        chunks = extrair_chunks_do_pdf(pdf_bytes)
        total_pages = max((c["numero_pagina"] for c in chunks), default=0)

        # ── Persiste chunks no banco ───────────────────────────────────────────
        logger.info(f"[{documento_id}] Salvando {len(chunks)} chunks no banco...")
        registros = [
            {
                "id":             str(uuid.uuid4()),
                "documento_id":   documento_id,
                "empresa_id":     empresa_id,
                "numero_pagina":  c["numero_pagina"],
                "chunk_index":    c["chunk_index"],
                "texto_original": c["texto_original"],
                "coordenadas":    c["coordenadas"],
                "font_name":      c.get("font_name"),
                "font_size":      c.get("font_size"),
                "block_type":     c.get("block_type", "text"),
                "status":         "pendente",
            }
            for c in chunks
        ]
        # Insert em lotes de 100 para não estourar limite do Supabase
        for i in range(0, len(registros), 100):
            sb.table("chunks_traducao").insert(registros[i:i+100]).execute()

        # Atualizar total de páginas no documento
        sb.table("documents").update({
            "status":      "extracted",
            "total_pages": total_pages,
        }).eq("id", documento_id).execute()

        # ── Etapa B: Tradução ──────────────────────────────────────────────────
        if model == "manual":
            logger.info(f"[{documento_id}] Modo manual selecionado. Pulando LLM...")
            sb.table("documents").update({"status": "translating"}).eq("id", documento_id).execute()

            res_chunks = sb.table("chunks_traducao") \
                .select("id, texto_original") \
                .eq("documento_id", documento_id) \
                .execute()

            for c in (res_chunks.data or []):
                sb.table("chunks_traducao").update({
                    "texto_traduzido_ia":    c["texto_original"],
                    "texto_final_revisado":  c["texto_original"],
                    "status":                "traduzido",
                    "model_used":            "manual",
                }).eq("id", c["id"]).execute()

            sb.table("documents").update({"status": "translated"}).eq("id", documento_id).execute()
            logger.info(f"[{documento_id}] ✅ Extração manual concluída com sucesso!")
            return

        logger.info(f"[{documento_id}] Carregando glossário da empresa {empresa_id}...")
        glossario = _carregar_glossario(empresa_id)
        glossario_str = _formatar_glossario_para_prompt(glossario)

        sb.table("documents").update({"status": "translating"}).eq("id", documento_id).execute()

        llm = ChatOpenAI(
            model=model,
            temperature=0.1,
            api_key=openai_api_key or os.environ.get("OPENAI_API_KEY"),
        )

        # Busca os IDs dos chunks inseridos (precisamos dos UUIDs)
        res_chunks = sb.table("chunks_traducao") \
            .select("id, texto_original") \
            .eq("documento_id", documento_id) \
            .order("numero_pagina,chunk_index") \
            .execute()

        todos = res_chunks.data or []
        logger.info(f"[{documento_id}] Traduzindo {len(todos)} chunks em lotes de {CHUNK_BATCH_SIZE}...")

        for i in range(0, len(todos), CHUNK_BATCH_SIZE):
            lote = todos[i:i + CHUNK_BATCH_SIZE]
            textos = [c["texto_original"] for c in lote]
            ids    = [c["id"] for c in lote]

            traducoes = await _traduzir_lote(textos, glossario_str, llm)

            # Atualizar cada chunk com sua tradução
            for chunk_id, traducao in zip(ids, traducoes):
                sb.table("chunks_traducao").update({
                    "texto_traduzido_ia":    traducao,
                    "texto_final_revisado":  traducao,  # espelho inicial
                    "status":                "traduzido",
                    "model_used":            model,
                }).eq("id", chunk_id).execute()

            logger.info(f"[{documento_id}] Lote {i // CHUNK_BATCH_SIZE + 1} concluído.")
            await asyncio.sleep(0.5)  # Throttle para respeitar rate limits

        # ── Finalização ───────────────────────────────────────────────────────
        sb.table("documents").update({"status": "translated"}).eq("id", documento_id).execute()
        logger.info(f"[{documento_id}] ✅ Pipeline concluído com sucesso!")

    except Exception as exc:
        logger.error(f"[{documento_id}] ❌ Erro no pipeline: {exc}", exc_info=True)
        sb.table("documents").update({
            "status":   "error",
            "metadata": {"error": str(exc)},
        }).eq("id", documento_id).execute()
        raise
