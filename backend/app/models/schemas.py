from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
import uuid


# ─── Enums ───────────────────────────────────────────────────────────────────

class DocumentStatus(str, Enum):
    uploaded       = "uploaded"
    processing     = "processing"
    extracted      = "extracted"
    translating    = "translating"
    translated     = "translated"
    reviewing      = "reviewing"
    approved       = "approved"
    exported       = "exported"
    error          = "error"


class ChunkStatus(str, Enum):
    pendente  = "pendente"
    traduzido = "traduzido"
    revisado  = "revisado"
    aprovado  = "aprovado"


# ─── Coordenadas ─────────────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    width:  float = Field(default=0)
    height: float = Field(default=0)


# ─── Empresa ─────────────────────────────────────────────────────────────────

class EmpresaOut(BaseModel):
    id:             str
    nome_comercial: str
    status:         bool
    plan:           str
    created_at:     datetime


# ─── Glossário ───────────────────────────────────────────────────────────────

class GlossarioItem(BaseModel):
    id:           Optional[str] = None
    empresa_id:   str
    termo_orig:   str
    termo_pt:     str
    contexto:     Optional[str] = None
    nao_traduzir: bool = False

class GlossarioCreate(BaseModel):
    termo_orig:   str
    termo_pt:     str
    contexto:     Optional[str] = None
    nao_traduzir: bool = False


# ─── Chunk de Tradução ───────────────────────────────────────────────────────

class ChunkOut(BaseModel):
    id:                   str
    documento_id:         str
    numero_pagina:        int
    chunk_index:          int
    texto_original:       str
    texto_traduzido_ia:   Optional[str] = None
    texto_final_revisado: Optional[str] = None
    coordenadas:          BoundingBox
    font_name:            Optional[str] = None
    font_size:            Optional[float] = None
    block_type:           str = "text"
    status:               ChunkStatus
    versao:               int = 1
    offset_x:             float = 0.0
    offset_y:             float = 0.0
    custom_font_size:     Optional[float] = None

class ChunkRevisaoUpdate(BaseModel):
    texto_final_revisado: str
    status:               ChunkStatus = ChunkStatus.revisado
    offset_x:             float = 0.0
    offset_y:             float = 0.0
    custom_font_size:     Optional[float] = None


# ─── Documento ───────────────────────────────────────────────────────────────

class DocumentoOut(BaseModel):
    id:               str
    empresa_id:       str
    nome_original:    str
    caminho_storage:  str
    status:           str
    versao_atual:     int
    total_pages:      Optional[int] = None
    source_language:  str
    target_language:  str
    progresso:        Optional[dict] = None
    created_at:       datetime

class DocumentoCreate(BaseModel):
    nome_original:    str
    source_language:  str = "de"
    target_language:  str = "pt"


# ─── Exportação ──────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    com_imagens:  bool = True     # True=PDF overlay | False=Markdown
    versao:       Optional[int] = None  # None = versão atual
    quebra_linha_manual: bool = False
    font_offset:  float = -2.0


# ─── Respostas Genéricas ─────────────────────────────────────────────────────

class ProgressoDocumento(BaseModel):
    total:      int
    pendente:   int
    traduzido:  int
    revisado:   int
    aprovado:   int
    percentual: float

class JobDispatchResponse(BaseModel):
    documento_id: str
    job_id:       str
    message:      str
