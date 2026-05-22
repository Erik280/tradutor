-- ============================================================
-- FIX: Garantir que super_admin pode ler todas as empresas
-- Execute no SQL Editor do Supabase
-- ============================================================

-- Adicionar política SELECT para super_admin na tabela companies
-- (pode já existir da migration 003, mas usando ON CONFLICT não dá erro)

DO $$
BEGIN
  -- Remove se existir para recriar limpa
  DROP POLICY IF EXISTS "companies_select_super_admin" ON public.companies;

  CREATE POLICY "companies_select_super_admin"
    ON public.companies FOR SELECT
    USING (
      EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'super_admin'
      )
    );
END $$;

-- Verificar: o usuário eriklima.me@gmail.com deve ter role = 'super_admin'
-- Rode este SELECT para confirmar:
SELECT id, email, role FROM public.profiles WHERE email = 'eriklima.me@gmail.com';
