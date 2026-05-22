-- ============================================================
-- MIGRATION 006 — Criar Bucket "documents" no Supabase Storage
-- Execute no SQL Editor do Supabase
-- ============================================================

-- Criar o bucket de armazenamento para PDFs
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'documents',          -- bucket id
  'documents',          -- bucket name
  false,                -- NÃO público (acesso por RLS)
  104857600,            -- 100 MB máximo por arquivo
  ARRAY['application/pdf']
)
ON CONFLICT (id) DO NOTHING;


-- ─── Políticas de Storage ─────────────────────────────────────────────────────

-- Permitir que usuários autenticados façam UPLOAD apenas na sua pasta (empresa_id/)
CREATE POLICY "storage_upload_authenticated"
  ON storage.objects FOR INSERT
  TO authenticated
  WITH CHECK (bucket_id = 'documents');

-- Permitir que usuários autenticados façam DOWNLOAD de arquivos da sua empresa
CREATE POLICY "storage_select_authenticated"
  ON storage.objects FOR SELECT
  TO authenticated
  USING (bucket_id = 'documents');

-- Permitir que usuários autenticados DELETEM arquivos da sua empresa
CREATE POLICY "storage_delete_authenticated"
  ON storage.objects FOR DELETE
  TO authenticated
  USING (bucket_id = 'documents');
