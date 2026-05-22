-- ============================================================
-- FIX DEFINITIVO DE TODAS AS POLÍTICAS RLS COM RECURSÃO INFINITA
-- ============================================================

-- 1. Função para verificar se é super_admin (já criada, mas garantindo)
CREATE OR REPLACE FUNCTION public.is_super_admin()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role = 'super_admin'
  );
$$;

-- 2. Função para verificar se é admin de uma empresa específica (bypassa RLS)
CREATE OR REPLACE FUNCTION public.is_company_admin(p_company_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.company_members
    WHERE company_id = p_company_id
      AND user_id = auth.uid()
      AND role IN ('admin', 'super_admin')
      AND is_active = TRUE
  );
$$;

-- 3. Limpar políticas bugadas na tabela profiles
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own" ON public.profiles FOR SELECT
  USING (auth.uid() = id OR public.is_super_admin());

-- 4. Limpar políticas bugadas na tabela companies
DROP POLICY IF EXISTS "companies_select_member" ON public.companies;
DROP POLICY IF EXISTS "companies_select_super_admin" ON public.companies;
CREATE POLICY "companies_select_member" ON public.companies FOR SELECT
  USING (
    public.is_super_admin()
    OR EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
  );

-- 5. Limpar políticas bugadas na tabela company_members (Causadora principal da recursão!)
DROP POLICY IF EXISTS "company_members_select" ON public.company_members;
CREATE POLICY "company_members_select" ON public.company_members FOR SELECT
  USING (
    user_id = auth.uid()
    OR public.is_super_admin()
    OR public.is_company_admin(company_id)
  );

DROP POLICY IF EXISTS "company_members_admin_manage" ON public.company_members;
CREATE POLICY "company_members_admin_manage" ON public.company_members FOR ALL
  USING (
    public.is_super_admin()
    OR public.is_company_admin(company_id)
  );

-- 6. Atualizar documentos
DROP POLICY IF EXISTS "documents_select_member" ON public.documents;
CREATE POLICY "documents_select_member" ON public.documents FOR SELECT
  USING (
    public.is_super_admin()
    OR EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
  );

DROP POLICY IF EXISTS "documents_insert_member" ON public.documents;
CREATE POLICY "documents_insert_member" ON public.documents FOR INSERT
  WITH CHECK (
    public.is_super_admin()
    OR EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid()
        AND cm.role IN ('admin', 'translator') AND cm.is_active = TRUE
    )
  );

-- Resolver outras tabelas (chunks_traducao, glossario) para segurança
DROP POLICY IF EXISTS "glossaries_select_member" ON public.glossaries;
CREATE POLICY "glossaries_select_member" ON public.glossaries FOR SELECT
  USING (
    public.is_super_admin()
    OR EXISTS (
      SELECT 1 FROM public.company_members cm
      WHERE cm.company_id = company_id AND cm.user_id = auth.uid() AND cm.is_active = TRUE
    )
  );
