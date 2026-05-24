"""
routers/documentos.py — FastAPI Router para documentos

Endpoints:
  POST   /documentos/upload              → Upload PDF + dispara BackgroundTask
  GET    /documentos                     → Lista documentos da empresa
  GET    /documentos/{id}                → Detalhes + progresso
  GET    /documentos/{id}/chunks         → Lista chunks (paginado por página)
  PATCH  /documentos/{id}/chunks/{cid}  → Salvar revisão humana
  POST   /documentos/{id}/exportar       → Exportar (overlay PDF ou Markdown)
  GET    /glossario                      → Listar termos do glossário
  POST   /glossario                      → Adicionar termo
  DELETE /glossario/{gid}               → Remover termo
"""

import os
import uuid
import logging
from typing import List, Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    HTTPException, Query, UploadFile, status, Request
)
from fastapi.responses import Response, StreamingResponse

from app.core.supabase_client import get_supabase
from app.models.schemas import (
    ChunkOut, ChunkRevisaoUpdate, DocumentoOut,
    ExportRequest, GlossarioCreate, GlossarioItem,
    JobDispatchResponse,
)
from app.services.translator_service import run_translation_pipeline
from app.services.export_service import gerar_pdf_overlay, gerar_markdown

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documentos", tags=["Documentos"])
glossario_router = APIRouter(prefix="/glossario", tags=["Glossário"])

MAX_FILE_MB = 100


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_token(request: Request) -> str:
    return request.headers.get("Authorization", "")

def _get_user_and_empresa_from_token(authorization: str) -> tuple[str, str]:
    """
    Valida o JWT do Supabase e retorna (empresa_id, user_id).
    """
    sb = get_supabase()
    token = authorization.replace("Bearer ", "")
    try:
        user = sb.auth.get_user(token)
        user_id = user.user.id

        # Buscar empresa_id do membro
        res = sb.table("company_members") \
            .select("company_id") \
            .eq("user_id", user_id) \
            .eq("is_active", True) \
            .limit(1) \
            .execute()

        if not res.data:
            raise HTTPException(status_code=403, detail="Usuário sem empresa associada.")
        return res.data[0]["company_id"], user_id
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Falha na autenticação: {exc}")
        raise HTTPException(status_code=401, detail="Token inválido.")


# ─── UPLOAD + DISPARO DO PIPELINE ────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=JobDispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload de PDF e início da tradução",
)
async def upload_documento(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_language: str = Form(default="de"),
    target_language: str = Form(default="pt"),
    model: str = Form(default="gpt-4o-mini"),
    authorization: str = Depends(get_token),
):
    """
    Recebe o PDF, faz upload para o Supabase Storage e dispara
    o pipeline de extração + tradução como BackgroundTask.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos.")

    conteudo = await file.read()
    tamanho_mb = len(conteudo) / (1024 * 1024)
    if tamanho_mb > MAX_FILE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande ({tamanho_mb:.1f} MB). Máximo: {MAX_FILE_MB} MB."
        )

    sb = get_supabase()
    empresa_id, user_id = _get_user_and_empresa_from_token(authorization)
    documento_id = str(uuid.uuid4())

    # Upload para o Supabase Storage
    # Supabase Storage rejects paths with spaces or special accents ("InvalidKey" 400 error)
    # We use the UUID as the filename in storage to guarantee a safe path.
    storage_path = f"{empresa_id}/{documento_id}/{documento_id}.pdf"
    try:
        sb.storage.from_("documents").upload(
            path=storage_path,
            file=conteudo,
            file_options={"content-type": "application/pdf"},
        )

        # Inserir registro na tabela documents
        sb.table("documents").insert({
            "id":              documento_id,
            "company_id":      empresa_id,
            "title":           file.filename,
            "original_filename": file.filename,
            "storage_path":    storage_path,
            "file_size_bytes": len(conteudo),
            "mime_type":       "application/pdf",
            "source_language": source_language,
            "target_language": target_language,
            "status":          "uploaded",
            "versao_atual":    1,
            "uploaded_by":     user_id,
        }).execute()
    except Exception as exc:
        logger.error(f"Erro no upload/insert: {exc}")
        raise HTTPException(status_code=500, detail=f"Erro interno de storage/bd: {str(exc)}")

    # Disparar pipeline assíncrono em background
    openai_key = os.environ.get("OPENAI_API_KEY")
    background_tasks.add_task(
        run_translation_pipeline,
        documento_id=documento_id,
        empresa_id=empresa_id,
        storage_path=storage_path,
        source_lang=source_language,
        target_lang=target_language,
        model=model,
        openai_api_key=openai_key,
    )

    return JobDispatchResponse(
        documento_id=documento_id,
        job_id=str(uuid.uuid4()),
        message=f"PDF '{file.filename}' recebido e tradução iniciada em background.",
    )


# ─── LISTAGEM DE DOCUMENTOS ───────────────────────────────────────────────────

@router.get("", response_model=List[dict], summary="Listar documentos da empresa")
async def listar_documentos(
    empresa_id_override: Optional[str] = Query(
        None, description="Apenas super_admin pode filtrar por empresa"
    ),
    authorization: str = Depends(get_token),
):
    sb = get_supabase()
    empresa_id, _ = _get_user_and_empresa_from_token(authorization)

    # Super admin pode passar empresa_id_override
    eid = empresa_id_override or empresa_id

    res = sb.table("documents") \
        .select("id,title,status,total_pages,source_language,target_language,created_at,versao_atual") \
        .eq("company_id", eid) \
        .order("created_at", desc=True) \
        .execute()

    documentos = res.data or []

    # Enriquecer com progresso de tradução
    for doc in documentos:
        prog_res = sb.rpc(
            "fn_progresso_documento", {"p_documento_id": doc["id"]}
        ).execute()
        doc["progresso"] = prog_res.data

    return documentos


# ─── DETALHES DO DOCUMENTO ────────────────────────────────────────────────────

@router.get("/{documento_id}", summary="Detalhes e progresso do documento")
async def detalhe_documento(
    documento_id: str,
    authorization: str = Depends(get_token),
):
    sb = get_supabase()
    _get_user_and_empresa_from_token(authorization)  # valida token

    res = sb.table("documents").select("*").eq("id", documento_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    prog_res = sb.rpc("fn_progresso_documento", {"p_documento_id": documento_id}).execute()
    doc = res.data
    doc["progresso"] = prog_res.data
    return doc


# ─── CHUNKS POR PÁGINA ────────────────────────────────────────────────────────

@router.get("/{documento_id}/chunks", summary="Lista chunks de uma página")
async def listar_chunks(
    documento_id: str,
    pagina: int = Query(1, ge=1),
    authorization: str = Depends(get_token),
):
    sb = get_supabase()
    _get_user_and_empresa_from_token(authorization)

    res = sb.table("chunks_traducao") \
        .select("*") \
        .eq("documento_id", documento_id) \
        .eq("numero_pagina", pagina) \
        .order("chunk_index") \
        .execute()

    return res.data or []


# ─── SALVAR REVISÃO HUMANA ────────────────────────────────────────────────────

@router.patch(
    "/{documento_id}/chunks/{chunk_id}",
    summary="Salvar texto revisado pelo humano",
)
async def revisar_chunk(
    documento_id: str,
    chunk_id: str,
    body: ChunkRevisaoUpdate,
    authorization: str = Depends(get_token),
):
    sb = get_supabase()
    _get_user_and_empresa_from_token(authorization)

    res = sb.table("chunks_traducao").update({
        "texto_final_revisado": body.texto_final_revisado,
        "status":               body.status.value,
        "offset_x":             body.offset_x,
        "offset_y":             body.offset_y,
        "custom_font_size":     body.custom_font_size,
    }).eq("id", chunk_id).eq("documento_id", documento_id).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Chunk não encontrado.")
    return res.data[0]


# ─── EXPORTAÇÃO ───────────────────────────────────────────────────────────────

@router.post("/{documento_id}/exportar", summary="Exportar documento traduzido")
async def exportar_documento(
    documento_id: str,
    body: ExportRequest,
    authorization: str = Depends(get_token),
):
    sb = get_supabase()
    try:
        _get_user_and_empresa_from_token(authorization)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

    # Buscar documento
    doc_res = sb.table("documents").select("*").eq("id", documento_id).single().execute()
    if not doc_res.data:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    doc = doc_res.data

    # Buscar todos os chunks traduzidos
    chunks_res = sb.table("chunks_traducao") \
        .select("*") \
        .eq("documento_id", documento_id) \
        .order("numero_pagina,chunk_index") \
        .execute()

    chunks = chunks_res.data or []
    if not chunks:
        raise HTTPException(status_code=400, detail="Nenhum chunk traduzido encontrado.")

    try:
        import urllib.parse
        nome_base = doc["title"].replace(".pdf", "")

        if body.com_imagens:
            # ── Modo: PDF Overlay ──────────────────────────────────────────────────
            logger.info(f"[{documento_id}] Gerando PDF overlay...")
            pdf_bytes = sb.storage.from_("documents").download(doc["storage_path"])
            pdf_final = gerar_pdf_overlay(
                pdf_bytes, 
                chunks, 
                quebra_linha_manual=body.quebra_linha_manual,
                font_offset=body.font_offset
            )

            nome_arquivo = f"{nome_base}_traduzido.pdf"
            nome_arquivo_encoded = urllib.parse.quote(nome_arquivo)

            return Response(
                content=pdf_final,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename*=utf-8''{nome_arquivo_encoded}"
                },
            )
        else:
            # ── Modo: Markdown ────────────────────────────────────────────────────
            logger.info(f"[{documento_id}] Gerando Markdown...")
            md_bytes = gerar_markdown(chunks, nome_documento=nome_base)

            nome_arquivo = f"{nome_base}_traduzido.md"
            nome_arquivo_encoded = urllib.parse.quote(nome_arquivo)

            return Response(
                content=md_bytes,
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename*=utf-8''{nome_arquivo_encoded}"
                },
            )
    except Exception as exc:
        logger.error(f"Erro na exportação [{documento_id}]: {exc}")
        raise HTTPException(status_code=500, detail=f"Falha na exportação: {str(exc)}")


# ─── GLOSSÁRIO ───────────────────────────────────────────────────────────────

@glossario_router.get("", summary="Listar termos do glossário da empresa")
async def listar_glossario(
    authorization: str = Depends(get_token),
):
    sb = get_supabase()
    empresa_id, _ = _get_user_and_empresa_from_token(authorization)

    res = sb.table("glossario") \
        .select("*") \
        .eq("empresa_id", empresa_id) \
        .order("termo_orig") \
        .execute()
    return res.data or []


@glossario_router.post("", status_code=201, summary="Adicionar termo ao glossário")
async def adicionar_termo(
    body: GlossarioCreate,
    authorization: str = Depends(get_token),
):
    sb = get_supabase()
    empresa_id, _ = _get_user_and_empresa_from_token(authorization)

    res = sb.table("glossario").insert({
        "empresa_id":   empresa_id,
        "termo_orig":   body.termo_orig,
        "termo_pt":     body.termo_pt,
        "contexto":     body.contexto,
        "nao_traduzir": body.nao_traduzir,
    }).execute()

    return res.data[0]


@glossario_router.delete("/{termo_id}", status_code=204, summary="Remover termo")
async def remover_termo(
    termo_id: str,
    authorization: str = Depends(get_token),
):
    sb = get_supabase()
    empresa_id, _ = _get_user_and_empresa_from_token(authorization)

    sb.table("glossario") \
        .delete() \
        .eq("id", termo_id) \
        .eq("empresa_id", empresa_id) \
        .execute()
    return None
