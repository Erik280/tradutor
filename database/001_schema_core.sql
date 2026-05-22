-- ============================================================
-- MIGRATION 001 — Core Schema: Extensions, Enums & Helpers
-- Projeto: Tradutor Técnico SaaS
-- Autor: Clawdirene (Arquiteta Principal)
-- ============================================================

-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Full-text search em glossários
CREATE EXTENSION IF NOT EXISTS "unaccent";  -- Busca sem acento

-- ─── Enums ───────────────────────────────────────────────────────────────────

-- Papel global no sistema (hierarquia raiz)
CREATE TYPE public.system_role AS ENUM (
  'super_admin',   -- Root total — Erik Lima
  'admin',         -- Admin de empresa
  'translator',    -- Tradutor
  'reviewer',      -- Revisor
  'viewer'         -- Apenas leitura
);

-- Status do documento
CREATE TYPE public.document_status AS ENUM (
  'uploaded',       -- Subido, aguardando processamento
  'processing',     -- Extração em andamento
  'extracted',      -- Texto extraído com sucesso
  'translating',    -- Tradução em andamento
  'translated',     -- Tradução concluída
  'reviewing',      -- Em revisão
  'approved',       -- Aprovado
  'exported',       -- Exportado
  'error'           -- Erro no processamento
);

-- Status de um segmento de texto
CREATE TYPE public.segment_status AS ENUM (
  'pending',        -- Aguardando tradução
  'translated',     -- Traduzido pela IA
  'reviewed',       -- Revisado manualmente
  'approved',       -- Aprovado pelo revisor
  'rejected'        -- Rejeitado para retradução
);

-- Tipo de exportação
CREATE TYPE public.export_format AS ENUM (
  'pdf_overlay',    -- PDF com overlay (preserva diagramas)
  'markdown',       -- Texto limpo em Markdown
  'docx'            -- Word (futuro)
);

-- Status do job de tradução
CREATE TYPE public.job_status AS ENUM (
  'queued',
  'running',
  'completed',
  'failed',
  'cancelled'
);

-- ─── Helper: updated_at automático ────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ─── Helper: cria perfil automático ao criar usuário auth ─────────────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, role)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    'viewer'::public.system_role
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
