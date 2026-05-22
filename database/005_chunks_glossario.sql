-- ============================================================
-- MIGRATION 005 — Schema Simplificado do Núcleo de Tradução
-- Tabelas operacionais: empresas, usuarios, documentos,
-- chunks_traducao, glossario
-- Compatível com o schema base (001-004 já executados)
-- ============================================================

-- ─── EMPRESAS (alias para companies já existente) ─────────────────────────────
-- Criamos uma VIEW para manter compatibilidade com o código novo
CREATE OR REPLACE VIEW public.empresas AS
  SELECT
    id,
    name            AS nome_comercial,
    is_active       AS status,
    plan,
    created_at,
    created_by
  FROM public.companies;

-- ─── USUARIOS (view sobre profiles + company_members) ────────────────────────
CREATE OR REPLACE VIEW public.usuarios AS
  SELECT
    p.id,
    cm.company_id   AS empresa_id,
    p.full_name     AS nome,
    p.email,
    p.role,         -- super_admin | admin | translator | reviewer | viewer
    p.is_active,
    p.created_at
  FROM public.profiles p
  LEFT JOIN public.company_members cm ON cm.user_id = p.id AND cm.is_active = TRUE;


-- ─── DOCUMENTOS (tabela operacional principal) ────────────────────────────────
-- Substituímos / complementamos public.documents com colunas específicas
ALTER TABLE public.documents
  ADD COLUMN IF NOT EXISTS versao_atual INTEGER NOT NULL DEFAULT 1;

-- View para uso no código com nomes pt-BR
CREATE OR REPLACE VIEW public.documentos AS
  SELECT
    id,
    company_id      AS empresa_id,
    uploaded_by     AS usuario_id,
    title           AS nome_original,
    storage_path    AS caminho_storage,
    status::TEXT    AS status,
    versao_atual,
    total_pages,
    source_language,
    target_language,
    created_at,
    updated_at
  FROM public.documents;


-- ─── CHUNKS DE TRADUÇÃO ───────────────────────────────────────────────────────
-- Tabela central: cada bloco de texto de uma página com coordenadas e traduções
CREATE TABLE IF NOT EXISTS public.chunks_traducao (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  documento_id          UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
  empresa_id            UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  numero_pagina         INTEGER NOT NULL,
  chunk_index           INTEGER NOT NULL,       -- ordem dentro da página
  texto_original        TEXT NOT NULL,
  texto_traduzido_ia    TEXT,                   -- saída bruta da LLM
  texto_final_revisado  TEXT,                   -- versão humana final
  coordenadas           JSONB NOT NULL DEFAULT '{}'::JSONB,  -- {x0, y0, x1, y1, width_pts, height_pts}
  font_name             TEXT,
  font_size             NUMERIC,
  block_type            TEXT DEFAULT 'text',    -- text | heading | table | caption | ignore
  status                TEXT NOT NULL DEFAULT 'pendente',
                        -- pendente | traduzido | revisado | aprovado
  versao                INTEGER NOT NULL DEFAULT 1,
  model_used            TEXT,
  prompt_tokens         INTEGER,
  completion_tokens     INTEGER,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (documento_id, numero_pagina, chunk_index, versao)
);

CREATE INDEX idx_chunks_documento   ON public.chunks_traducao(documento_id);
CREATE INDEX idx_chunks_empresa     ON public.chunks_traducao(empresa_id);
CREATE INDEX idx_chunks_pagina      ON public.chunks_traducao(documento_id, numero_pagina);
CREATE INDEX idx_chunks_status      ON public.chunks_traducao(status);

CREATE TRIGGER trg_chunks_updated_at
  BEFORE UPDATE ON public.chunks_traducao
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

COMMENT ON TABLE public.chunks_traducao IS
  'Blocos de texto extraídos do PDF com coordenadas espaciais e traduções versionadas';
COMMENT ON COLUMN public.chunks_traducao.coordenadas IS
  'JSON: {x0, y0, x1, y1} em pontos PDF (origem bottom-left) + width/height em pts';


-- ─── GLOSSÁRIO ────────────────────────────────────────────────────────────────
-- Tabela simples e direta isolada por empresa
CREATE TABLE IF NOT EXISTS public.glossario (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  empresa_id  UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  termo_orig  TEXT NOT NULL,   -- Termo na língua original (ex: "Spindle")
  termo_pt    TEXT NOT NULL,   -- Tradução oficial da empresa (ex: "Fuso")
  contexto    TEXT,            -- Nota de uso opcional
  nao_traduzir BOOLEAN NOT NULL DEFAULT FALSE, -- Manter sempre em inglês
  criado_por  UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (empresa_id, termo_orig)
);

CREATE INDEX idx_glossario_empresa ON public.glossario(empresa_id);
-- Full-text search rápido em termos
CREATE INDEX idx_glossario_termo_trgm ON public.glossario
  USING GIN (termo_orig gin_trgm_ops);

CREATE TRIGGER trg_glossario_updated_at
  BEFORE UPDATE ON public.glossario
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

COMMENT ON TABLE public.glossario IS
  'Glossário técnico por empresa — substitui termos durante a tradução via LLM';


-- ─── RLS: CHUNKS DE TRADUÇÃO ─────────────────────────────────────────────────
ALTER TABLE public.chunks_traducao ENABLE ROW LEVEL SECURITY;

CREATE POLICY "chunks_select_member"
  ON public.chunks_traducao FOR SELECT
  USING (
    empresa_id IN (
      SELECT cm.company_id FROM public.company_members cm
      WHERE cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "chunks_insert_backend"
  ON public.chunks_traducao FOR INSERT
  WITH CHECK (
    empresa_id IN (
      SELECT cm.company_id FROM public.company_members cm
      WHERE cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "chunks_update_reviewer"
  ON public.chunks_traducao FOR UPDATE
  USING (
    empresa_id IN (
      SELECT cm.company_id FROM public.company_members cm
      WHERE cm.user_id = auth.uid()
        AND cm.role IN ('reviewer', 'admin', 'super_admin')
        AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );


-- ─── RLS: GLOSSÁRIO ──────────────────────────────────────────────────────────
ALTER TABLE public.glossario ENABLE ROW LEVEL SECURITY;

CREATE POLICY "glossario_select_member"
  ON public.glossario FOR SELECT
  USING (
    empresa_id IN (
      SELECT cm.company_id FROM public.company_members cm
      WHERE cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "glossario_manage_member"
  ON public.glossario FOR ALL
  USING (
    empresa_id IN (
      SELECT cm.company_id FROM public.company_members cm
      WHERE cm.user_id = auth.uid()
        AND cm.role IN ('translator', 'reviewer', 'admin', 'super_admin')
        AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );


-- ─── FUNÇÃO: Progresso de tradução do documento ───────────────────────────────
CREATE OR REPLACE FUNCTION public.fn_progresso_documento(p_documento_id UUID)
RETURNS JSONB AS $$
  SELECT jsonb_build_object(
    'total',      COUNT(*),
    'pendente',   COUNT(*) FILTER (WHERE status = 'pendente'),
    'traduzido',  COUNT(*) FILTER (WHERE status = 'traduzido'),
    'revisado',   COUNT(*) FILTER (WHERE status = 'revisado'),
    'aprovado',   COUNT(*) FILTER (WHERE status = 'aprovado'),
    'percentual', ROUND(
      COUNT(*) FILTER (WHERE status IN ('traduzido','revisado','aprovado'))::NUMERIC
      / NULLIF(COUNT(*), 0) * 100, 1
    )
  )
  FROM public.chunks_traducao
  WHERE documento_id = p_documento_id;
$$ LANGUAGE SQL STABLE SECURITY DEFINER;
