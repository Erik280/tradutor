-- ============================================================
-- MIGRATION 004 — Super Admin Seed
-- Eleva eriklima.me@gmail.com ao papel de super_admin (root)
-- ID do usuário: 2421096d-9c99-4a9d-809b-f018ee80a5c5
-- ============================================================

-- 1. Garantir que o perfil existe (caso o trigger não tenha rodado)
INSERT INTO public.profiles (id, email, full_name, role, is_active)
VALUES (
  '2421096d-9c99-4a9d-809b-f018ee80a5c5',
  'eriklima.me@gmail.com',
  'Erik Lima',
  'super_admin',
  TRUE
)
ON CONFLICT (id) DO UPDATE SET
  role       = 'super_admin',
  full_name  = COALESCE(EXCLUDED.full_name, public.profiles.full_name),
  is_active  = TRUE,
  updated_at = NOW();

-- 2. Verificação — deve retornar uma linha com role = 'super_admin'
SELECT
  id,
  email,
  full_name,
  role,
  is_active,
  created_at
FROM public.profiles
WHERE id = '2421096d-9c99-4a9d-809b-f018ee80a5c5';


-- ─── Empresa Root (opcional — para o super admin ter uma home) ────────────────

INSERT INTO public.companies (id, name, slug, plan, is_active, created_by)
VALUES (
  'aaaaaaaa-0000-0000-0000-000000000001',
  'TransformaFuturo (Root)',
  'transformafuturo-root',
  'enterprise',
  TRUE,
  '2421096d-9c99-4a9d-809b-f018ee80a5c5'
)
ON CONFLICT (slug) DO NOTHING;

-- Adicionar super admin como membro root da empresa raiz
INSERT INTO public.company_members (company_id, user_id, role, is_active)
VALUES (
  'aaaaaaaa-0000-0000-0000-000000000001',
  '2421096d-9c99-4a9d-809b-f018ee80a5c5',
  'super_admin',
  TRUE
)
ON CONFLICT (company_id, user_id) DO UPDATE SET
  role      = 'super_admin',
  is_active = TRUE;

-- ─── Verificação final ────────────────────────────────────────────────────────
SELECT
  p.email,
  p.role          AS system_role,
  c.name          AS company_name,
  cm.role         AS company_role
FROM public.profiles p
LEFT JOIN public.company_members cm ON cm.user_id = p.id
LEFT JOIN public.companies c ON c.id = cm.company_id
WHERE p.email = 'eriklima.me@gmail.com';
