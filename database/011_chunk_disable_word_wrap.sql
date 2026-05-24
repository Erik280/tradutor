-- 011_chunk_disable_word_wrap.sql
-- Adiciona coluna para desativar quebra automática de linha individualmente por chunk

ALTER TABLE public.chunks_traducao
ADD COLUMN IF NOT EXISTS disable_word_wrap BOOLEAN DEFAULT FALSE;
