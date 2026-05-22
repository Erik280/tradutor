import { supabase } from "@/lib/supabase";

const API_BASE = import.meta.env.VITE_API_URL ?? "https://api.tradutor.transformafuturo.com.br/api/v1";

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token ?? "";
  return { Authorization: `Bearer ${token}` };
}

export const api = {
  // ─── Documentos ──────────────────────────────────────────────────────────────
  async listarDocumentos(empresaId?: string) {
    const headers = await getAuthHeaders();
    const url = new URL(`${API_BASE}/documentos`);
    if (empresaId) url.searchParams.set("empresa_id_override", empresaId);
    const res = await fetch(url.toString(), { headers });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async detalheDocumento(id: string) {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/documentos/${id}`, { headers });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async uploadDocumento(file: File, sourceLang = "de", targetLang = "pt", model = "gpt-4o-mini") {
    const headers = await getAuthHeaders();
    const fd = new FormData();
    fd.append("file", file);
    fd.append("source_language", sourceLang);
    fd.append("target_language", targetLang);
    fd.append("model", model);
    const res = await fetch(`${API_BASE}/documentos/upload`, {
      method: "POST",
      headers,
      body: fd,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async listarChunks(documentoId: string, pagina: number) {
    const headers = await getAuthHeaders();
    const res = await fetch(
      `${API_BASE}/documentos/${documentoId}/chunks?pagina=${pagina}`,
      { headers }
    );
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async salvarRevisao(documentoId: string, chunkId: string, texto: string) {
    const headers = await getAuthHeaders();
    const res = await fetch(
      `${API_BASE}/documentos/${documentoId}/chunks/${chunkId}`,
      {
        method: "PATCH",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ texto_final_revisado: texto, status: "revisado" }),
      }
    );
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async exportarDocumento(documentoId: string, comImagens: boolean): Promise<Blob> {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/documentos/${documentoId}/exportar`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ com_imagens: comImagens }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.blob();
  },

  // ─── Glossário ────────────────────────────────────────────────────────────
  async listarGlossario() {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/glossario`, { headers });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async adicionarTermo(termo_orig: string, termo_pt: string, contexto?: string) {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/glossario`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ termo_orig, termo_pt, contexto }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async removerTermo(id: string) {
    const headers = await getAuthHeaders();
    await fetch(`${API_BASE}/glossario/${id}`, { method: "DELETE", headers });
  },
};
