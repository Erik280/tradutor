-- ============================================================
-- FIX: Resolver erro 500 (Recursão infinita no RLS)
-- ============================================================

-- 1. Criar função SECURITY DEFINER (bypassa o RLS para checar o role sem loop)
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

-- 2. Corrigir a política na tabela profiles (que causava o loop)
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own"
  ON public.profiles FOR SELECT
  USING (
    auth.uid() = id
    OR public.is_super_admin()
  );

-- 3. Corrigir a política na tabela companies
DROP POLICY IF EXISTS "companies_select_super_admin" ON public.companies;
CREATE POLICY "companies_select_super_admin"
  ON public.companies FOR SELECT
  USING (
    public.is_super_admin()
  );
