-- ============================================================
-- MIGRATION 003 — Row Level Security (RLS)
-- Políticas de segurança por linha para isolamento multi-tenant
-- ============================================================

-- ─── PROFILES ────────────────────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Usuário vê apenas o próprio perfil (ou super_admin vê todos)
CREATE POLICY "profiles_select_own"
  ON public.profiles FOR SELECT
  USING (
    auth.uid() = id
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

-- Usuário edita apenas o próprio perfil
CREATE POLICY "profiles_update_own"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Super admin pode inserir/atualizar qualquer perfil
CREATE POLICY "profiles_superadmin_all"
  ON public.profiles FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );


-- ─── COMPANIES ───────────────────────────────────────────────────────────────
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;

-- Membro da empresa lê a empresa
CREATE POLICY "companies_select_member"
  ON public.companies FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

-- Apenas super_admin cria/edita empresas
CREATE POLICY "companies_superadmin_all"
  ON public.companies FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

-- Admin da empresa pode atualizar configurações da sua empresa
CREATE POLICY "companies_admin_update"
  ON public.companies FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = id
        AND cm.user_id = auth.uid()
        AND cm.role IN ('admin', 'super_admin')
        AND cm.is_active = TRUE
    )
  );


-- ─── COMPANY_MEMBERS ─────────────────────────────────────────────────────────
ALTER TABLE public.company_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "company_members_select"
  ON public.company_members FOR SELECT
  USING (
    user_id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid()
        AND cm.role IN ('admin', 'super_admin') AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "company_members_admin_manage"
  ON public.company_members FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
    OR EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid()
        AND cm.role = 'admin' AND cm.is_active = TRUE
    )
  );


-- ─── DOCUMENTS ───────────────────────────────────────────────────────────────
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "documents_select_member"
  ON public.documents FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "documents_insert_member"
  ON public.documents FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid()
        AND cm.role IN ('admin', 'translator') AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "documents_update_member"
  ON public.documents FOR UPDATE
  USING (
    uploaded_by = auth.uid()
    OR EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid()
        AND cm.role IN ('admin', 'super_admin') AND cm.is_active = TRUE
    )
  );


-- ─── DOCUMENT_PAGES ──────────────────────────────────────────────────────────
ALTER TABLE public.document_pages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pages_select_via_document"
  ON public.document_pages FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.documents d
      JOIN public.company_members cm ON cm.company_id = d.company_id
      WHERE d.id = document_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "pages_insert_service"
  ON public.document_pages FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );


-- ─── TEXT_SEGMENTS ───────────────────────────────────────────────────────────
ALTER TABLE public.text_segments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "segments_select_via_document"
  ON public.text_segments FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.documents d
      JOIN public.company_members cm ON cm.company_id = d.company_id
      WHERE d.id = document_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );


-- ─── TRANSLATIONS ────────────────────────────────────────────────────────────
ALTER TABLE public.translations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "translations_select_via_segment"
  ON public.translations FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.text_segments ts
      JOIN public.documents d ON d.id = ts.document_id
      JOIN public.company_members cm ON cm.company_id = d.company_id
      WHERE ts.id = segment_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "translations_update_reviewer"
  ON public.translations FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.text_segments ts
      JOIN public.documents d ON d.id = ts.document_id
      JOIN public.company_members cm ON cm.company_id = d.company_id
      WHERE ts.id = segment_id
        AND cm.user_id = auth.uid()
        AND cm.role IN ('reviewer', 'admin', 'super_admin')
        AND cm.is_active = TRUE
    )
  );


-- ─── GLOSSARIES & TERMS ──────────────────────────────────────────────────────
ALTER TABLE public.glossaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.glossary_terms ENABLE ROW LEVEL SECURITY;

CREATE POLICY "glossaries_select_member"
  ON public.glossaries FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "glossaries_manage_admin"
  ON public.glossaries FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid()
        AND cm.role IN ('admin', 'super_admin') AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "glossary_terms_select"
  ON public.glossary_terms FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.glossaries g
      JOIN public.company_members cm ON cm.company_id = g.company_id
      WHERE g.id = glossary_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );

CREATE POLICY "glossary_terms_manage"
  ON public.glossary_terms FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.glossaries g
      JOIN public.company_members cm ON cm.company_id = g.company_id
      WHERE g.id = glossary_id AND cm.user_id = auth.uid()
        AND cm.role IN ('admin', 'translator', 'super_admin') AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );


-- ─── TRANSLATION_JOBS ────────────────────────────────────────────────────────
ALTER TABLE public.translation_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "jobs_select_member"
  ON public.translation_jobs FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );


-- ─── EXPORTS ─────────────────────────────────────────────────────────────────
ALTER TABLE public.exports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "exports_select_member"
  ON public.exports FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );


-- ─── AUDIT_LOGS ──────────────────────────────────────────────────────────────
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "audit_logs_select"
  ON public.audit_logs FOR SELECT
  USING (
    company_id IN (
      SELECT cm.company_id FROM public.company_members cm
      WHERE cm.user_id = auth.uid() AND cm.role IN ('admin', 'super_admin') AND cm.is_active = TRUE
    )
    OR EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.role = 'super_admin'
    )
  );
