-- 010_chunk_layout_controls.sql
-- Adiciona colunas para controle manual de posicionamento e tamanho de fonte por bloco (chunk).

ALTER TABLE public.chunks_traducao
ADD COLUMN IF NOT EXISTS offset_x FLOAT DEFAULT 0,
ADD COLUMN IF NOT EXISTS offset_y FLOAT DEFAULT 0,
ADD COLUMN IF NOT EXISTS custom_font_size FLOAT NULL;

-- Atualizar metadados para garantir que a permissão de update contemple essas colunas 
-- (Se já houver uma política de update ampla, isso será automático).
