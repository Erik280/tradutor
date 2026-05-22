-- ============================================================
-- MIGRATION 002 — Tabelas Principais
-- ============================================================

-- ─── PROFILES ────────────────────────────────────────────────────────────────
-- Estende auth.users com dados de perfil e papel global

CREATE TABLE IF NOT EXISTS public.profiles (
  id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email           TEXT NOT NULL UNIQUE,
  full_name       TEXT,
  avatar_url      TEXT,
  role            public.system_role NOT NULL DEFAULT 'viewer',
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Trigger: cria perfil quando novo usuário auth é criado
CREATE OR REPLACE TRIGGER trg_on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

COMMENT ON TABLE public.profiles IS 'Perfis de usuários — extensão de auth.users com role e metadados';
COMMENT ON COLUMN public.profiles.role IS 'super_admin = acesso total ao SaaS; admin = gestor de empresa; etc.';


-- ─── COMPANIES (TENANTS) ──────────────────────────────────────────────────────
-- Cada empresa é um tenant isolado no sistema multi-tenant

CREATE TABLE IF NOT EXISTS public.companies (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name            TEXT NOT NULL,
  slug            TEXT NOT NULL UNIQUE,  -- ex: "acme-industrias"
  logo_url        TEXT,
  plan            TEXT NOT NULL DEFAULT 'trial',  -- trial | starter | pro | enterprise
  plan_expires_at TIMESTAMPTZ,
  max_users       INTEGER NOT NULL DEFAULT 5,
  max_documents   INTEGER NOT NULL DEFAULT 50,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  settings        JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_by      UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_companies_updated_at
  BEFORE UPDATE ON public.companies
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

COMMENT ON TABLE public.companies IS 'Empresas/tenants do SaaS multi-tenant';


-- ─── COMPANY_MEMBERS ─────────────────────────────────────────────────────────
-- Relacionamento N:N entre usuários e empresas, com papel por empresa

CREATE TABLE IF NOT EXISTS public.company_members (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id      UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  role            public.system_role NOT NULL DEFAULT 'viewer',
  invited_by      UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  joined_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (company_id, user_id)
);

CREATE INDEX idx_company_members_company ON public.company_members(company_id);
CREATE INDEX idx_company_members_user    ON public.company_members(user_id);

COMMENT ON TABLE public.company_members IS 'Membros por empresa com papel específico';


-- ─── DOCUMENTS ───────────────────────────────────────────────────────────────
-- PDFs subidos para tradução

CREATE TABLE IF NOT EXISTS public.documents (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id        UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  uploaded_by       UUID NOT NULL REFERENCES public.profiles(id) ON DELETE SET NULL,
  title             TEXT NOT NULL,
  description       TEXT,
  original_filename TEXT NOT NULL,
  storage_path      TEXT NOT NULL,  -- Caminho no Supabase Storage
  file_size_bytes   BIGINT,
  mime_type         TEXT NOT NULL DEFAULT 'application/pdf',
  total_pages       INTEGER,
  source_language   TEXT NOT NULL DEFAULT 'de',  -- ISO 639-1
  target_language   TEXT NOT NULL DEFAULT 'pt',
  status            public.document_status NOT NULL DEFAULT 'uploaded',
  metadata          JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_company    ON public.documents(company_id);
CREATE INDEX idx_documents_status     ON public.documents(status);
CREATE INDEX idx_documents_uploaded   ON public.documents(uploaded_by);

CREATE TRIGGER trg_documents_updated_at
  BEFORE UPDATE ON public.documents
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

COMMENT ON TABLE public.documents IS 'PDFs de manuais técnicos subidos pelos tenants';


-- ─── DOCUMENT_PAGES ──────────────────────────────────────────────────────────
-- Cada página extraída do PDF

CREATE TABLE IF NOT EXISTS public.document_pages (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id     UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
  page_number     INTEGER NOT NULL,
  width_pts       NUMERIC,   -- Dimensões em pontos PDF
  height_pts      NUMERIC,
  thumbnail_path  TEXT,      -- Imagem preview da página no Storage
  raw_text        TEXT,      -- Texto completo extraído (concatenado)
  extraction_meta JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (document_id, page_number)
);

CREATE INDEX idx_pages_document ON public.document_pages(document_id);

COMMENT ON TABLE public.document_pages IS 'Páginas individuais extraídas dos PDFs';


-- ─── TEXT_SEGMENTS ───────────────────────────────────────────────────────────
-- Blocos de texto com coordenadas espaciais (para overlay PDF)

CREATE TABLE IF NOT EXISTS public.text_segments (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  page_id         UUID NOT NULL REFERENCES public.document_pages(id) ON DELETE CASCADE,
  document_id     UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
  segment_index   INTEGER NOT NULL,   -- Ordem no documento
  original_text   TEXT NOT NULL,
  -- Coordenadas do bounding box (em pontos PDF, origem bottom-left)
  bbox_x          NUMERIC,
  bbox_y          NUMERIC,
  bbox_width      NUMERIC,
  bbox_height     NUMERIC,
  font_name       TEXT,
  font_size       NUMERIC,
  is_bold         BOOLEAN DEFAULT FALSE,
  is_italic       BOOLEAN DEFAULT FALSE,
  block_type      TEXT DEFAULT 'text',  -- text | heading | table | caption
  status          public.segment_status NOT NULL DEFAULT 'pending',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_segments_page     ON public.text_segments(page_id);
CREATE INDEX idx_segments_document ON public.text_segments(document_id);
CREATE INDEX idx_segments_status   ON public.text_segments(status);

CREATE TRIGGER trg_segments_updated_at
  BEFORE UPDATE ON public.text_segments
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

COMMENT ON TABLE public.text_segments IS 'Blocos de texto com coordenadas espaciais para overlay de tradução';


-- ─── TRANSLATIONS ────────────────────────────────────────────────────────────
-- Tradução de cada segmento (pode ter histórico de versões)

CREATE TABLE IF NOT EXISTS public.translations (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  segment_id      UUID NOT NULL REFERENCES public.text_segments(id) ON DELETE CASCADE,
  translated_text TEXT NOT NULL,
  model_used      TEXT,          -- ex: "gpt-4o", "gemini-1.5-pro"
  prompt_tokens   INTEGER,
  completion_tokens INTEGER,
  is_current      BOOLEAN NOT NULL DEFAULT TRUE,  -- Versão ativa
  reviewed_by     UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  reviewed_at     TIMESTAMPTZ,
  notes           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_translations_segment ON public.translations(segment_id);
CREATE INDEX idx_translations_current ON public.translations(segment_id) WHERE is_current = TRUE;

COMMENT ON TABLE public.translations IS 'Traduções dos segmentos — versionadas com histórico';


-- ─── GLOSSARIES ──────────────────────────────────────────────────────────────
-- Glossário personalizado por empresa

CREATE TABLE IF NOT EXISTS public.glossaries (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id      UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  description     TEXT,
  source_language TEXT NOT NULL DEFAULT 'de',
  target_language TEXT NOT NULL DEFAULT 'pt',
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_by      UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (company_id, name)
);

CREATE TRIGGER trg_glossaries_updated_at
  BEFORE UPDATE ON public.glossaries
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

COMMENT ON TABLE public.glossaries IS 'Glossários por empresa para tradução especializada';


-- ─── GLOSSARY_TERMS ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.glossary_terms (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  glossary_id     UUID NOT NULL REFERENCES public.glossaries(id) ON DELETE CASCADE,
  source_term     TEXT NOT NULL,
  target_term     TEXT NOT NULL,
  context_note    TEXT,           -- Observação de uso
  is_do_not_translate BOOLEAN NOT NULL DEFAULT FALSE,
  created_by      UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (glossary_id, source_term)
);

-- Índice para busca rápida por termo (pg_trgm)
CREATE INDEX idx_glossary_terms_source_trgm ON public.glossary_terms
  USING GIN (source_term gin_trgm_ops);

CREATE TRIGGER trg_glossary_terms_updated_at
  BEFORE UPDATE ON public.glossary_terms
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

COMMENT ON TABLE public.glossary_terms IS 'Termos individuais dos glossários com source → target';


-- ─── TRANSLATION_JOBS ────────────────────────────────────────────────────────
-- Fila de jobs de tradução (processamento assíncrono)

CREATE TABLE IF NOT EXISTS public.translation_jobs (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id     UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
  company_id      UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  glossary_id     UUID REFERENCES public.glossaries(id) ON DELETE SET NULL,
  status          public.job_status NOT NULL DEFAULT 'queued',
  model_config    JSONB NOT NULL DEFAULT '{}'::JSONB,  -- modelo, temperatura, etc.
  segments_total  INTEGER DEFAULT 0,
  segments_done   INTEGER DEFAULT 0,
  error_message   TEXT,
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  created_by      UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jobs_document ON public.translation_jobs(document_id);
CREATE INDEX idx_jobs_status   ON public.translation_jobs(status);

CREATE TRIGGER trg_jobs_updated_at
  BEFORE UPDATE ON public.translation_jobs
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

COMMENT ON TABLE public.translation_jobs IS 'Fila de jobs de tradução assíncrona';


-- ─── EXPORTS ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.exports (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id     UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
  company_id      UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  format          public.export_format NOT NULL,
  storage_path    TEXT,           -- Arquivo gerado no Supabase Storage
  file_size_bytes BIGINT,
  status          public.job_status NOT NULL DEFAULT 'queued',
  error_message   TEXT,
  created_by      UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_exports_document ON public.exports(document_id);

COMMENT ON TABLE public.exports IS 'Exportações geradas (PDF overlay ou Markdown)';


-- ─── AUDIT_LOGS ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.audit_logs (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id      UUID REFERENCES public.companies(id) ON DELETE SET NULL,
  user_id         UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  action          TEXT NOT NULL,   -- ex: "document.upload", "translation.approve"
  table_name      TEXT,
  record_id       UUID,
  old_data        JSONB,
  new_data        JSONB,
  ip_address      INET,
  user_agent      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_company  ON public.audit_logs(company_id);
CREATE INDEX idx_audit_user     ON public.audit_logs(user_id);
CREATE INDEX idx_audit_action   ON public.audit_logs(action);
CREATE INDEX idx_audit_created  ON public.audit_logs(created_at DESC);

COMMENT ON TABLE public.audit_logs IS 'Log de auditoria de todas as ações relevantes do sistema';
