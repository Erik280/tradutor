import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Save, BookOpen, Check, ChevronLeft,
  ChevronRight, Loader2, Plus, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import ExportModal from "@/components/ExportModal";

interface Chunk {
  id: string;
  numero_pagina: number;
  chunk_index: number;
  texto_original: string;
  texto_traduzido_ia: string | null;
  texto_final_revisado: string | null;
  block_type: string;
  status: string;
}

interface AddTermState {
  show: boolean;
  original: string;
  traducao: string;
}

export default function ReviewPage() {
  const { documentoId } = useParams<{ documentoId: string }>();
  const navigate = useNavigate();

  const [documento,       setDocumento]       = useState<any>(null);
  const [chunks,          setChunks]          = useState<Chunk[]>([]);
  const [paginaAtual,     setPaginaAtual]      = useState(1);
  const [totalPaginas,    setTotalPaginas]     = useState(1);
  const [loading,         setLoading]          = useState(true);
  const [saving,          setSaving]           = useState<string | null>(null);  // chunk id sendo salvo
  const [savedIds,        setSavedIds]         = useState<Set<string>>(new Set());
  const [editando,        setEditando]         = useState<Record<string, string>>({});
  const [showExport,      setShowExport]       = useState(false);
  const [addTerm,         setAddTerm]          = useState<AddTermState>({ show: false, original: "", traducao: "" });

  // ── Carregar documento e chunks ───────────────────────────────────────────
  useEffect(() => {
    if (!documentoId) return;
    (async () => {
      const doc = await api.detalheDocumento(documentoId);
      setDocumento(doc);
      setTotalPaginas(doc.total_pages ?? 1);
    })();
  }, [documentoId]);

  const carregarChunks = useCallback(async () => {
    if (!documentoId) return;
    setLoading(true);
    try {
      const data = await api.listarChunks(documentoId, paginaAtual);
      setChunks(data);
      // Inicializar edição com texto revisado ou traduzido
      const edit: Record<string, string> = {};
      for (const c of data) {
        edit[c.id] = c.texto_final_revisado ?? c.texto_traduzido_ia ?? "";
      }
      setEditando(edit);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [documentoId, paginaAtual]);

  useEffect(() => { carregarChunks(); }, [carregarChunks]);

  // ── Salvar revisão individual ─────────────────────────────────────────────
  async function salvarChunk(chunkId: string) {
    if (!documentoId) return;
    setSaving(chunkId);
    try {
      await api.salvarRevisao(documentoId, chunkId, editando[chunkId] ?? "");
      setSavedIds((prev) => new Set(prev).add(chunkId));
      setTimeout(() => {
        setSavedIds((prev) => { const s = new Set(prev); s.delete(chunkId); return s; });
      }, 2000);
    } catch (e: any) {
      alert(`Erro ao salvar: ${e.message}`);
    } finally {
      setSaving(null);
    }
  }

  // ── Adicionar termo ao glossário ──────────────────────────────────────────
  async function handleAddTerm() {
    if (!addTerm.original || !addTerm.traducao) return;
    try {
      await api.adicionarTermo(addTerm.original, addTerm.traducao);
      setAddTerm({ show: false, original: "", traducao: "" });
    } catch (e: any) {
      alert(`Erro: ${e.message}`);
    }
  }

  // ── Seleção de texto para sugerir glossário ───────────────────────────────
  function handleTextSelection() {
    const sel = window.getSelection()?.toString().trim();
    if (sel && sel.length > 2) {
      setAddTerm({ show: true, original: sel, traducao: "" });
    }
  }

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* ── Topbar ── */}
      <header className="border-b border-border bg-card px-4 py-3 flex items-center gap-3 shrink-0">
        <button
          onClick={() => navigate("/dashboard")}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Voltar
        </button>

        <div className="flex-1 min-w-0">
          <p className="font-semibold text-foreground truncate text-sm">
            {documento?.title ?? "Carregando..."}
          </p>
          <p className="text-xs text-muted-foreground">
            {documento?.source_language?.toUpperCase()} → {documento?.target_language?.toUpperCase()} ·
            Página {paginaAtual} de {totalPaginas}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Paginação */}
          <div className="flex items-center gap-1 border border-border rounded-lg overflow-hidden">
            <button
              id="btn-pagina-anterior"
              onClick={() => setPaginaAtual((p) => Math.max(1, p - 1))}
              disabled={paginaAtual === 1}
              className="px-2 py-1.5 hover:bg-accent disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-3 text-sm text-foreground tabular-nums">
              {paginaAtual} / {totalPaginas}
            </span>
            <button
              id="btn-proxima-pagina"
              onClick={() => setPaginaAtual((p) => Math.min(totalPaginas, p + 1))}
              disabled={paginaAtual === totalPaginas}
              className="px-2 py-1.5 hover:bg-accent disabled:opacity-40 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <button
            id="btn-glossario"
            onClick={() => setAddTerm((s) => ({ ...s, show: true }))}
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 border border-border rounded-lg hover:bg-accent transition-colors text-foreground"
          >
            <BookOpen className="w-4 h-4" />
            <span className="hidden sm:inline">Glossário</span>
          </button>

          <button
            id="btn-exportar"
            onClick={() => setShowExport(true)}
            className="flex items-center gap-1.5 text-sm px-4 py-1.5 rounded-lg text-white font-semibold transition-all hover:brightness-110"
            style={{ background: "oklch(0.6397 0.1720 36.4421)" }}
          >
            Exportar
          </button>
        </div>
      </header>

      {/* ── Split Screen ── */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : chunks.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <p>Nenhum bloco de texto nesta página.</p>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-2 overflow-hidden">
          {/* ── Coluna Esquerda: Original ── */}
          <div
            className="overflow-y-auto border-r border-border"
            style={{ background: "oklch(0.9846 0.0017 247.8389)" }}
          >
            <div className="sticky top-0 z-10 px-4 py-2 border-b border-border bg-muted/80 backdrop-blur-sm">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Texto Original — {documento?.source_language?.toUpperCase()}
              </p>
            </div>

            <div className="p-4 space-y-3">
              {chunks.map((chunk) => (
                <div
                  key={chunk.id}
                  className="bg-card border border-border rounded-xl p-4 text-sm text-foreground leading-relaxed"
                  onMouseUp={handleTextSelection}
                >
                  <span className="text-xs text-muted-foreground block mb-2 font-mono">
                    #{chunk.chunk_index + 1} · {chunk.block_type}
                  </span>
                  <p className="whitespace-pre-wrap">{chunk.texto_original}</p>
                </div>
              ))}
            </div>
          </div>

          {/* ── Coluna Direita: Tradução/Revisão ── */}
          <div className="overflow-y-auto bg-background">
            <div className="sticky top-0 z-10 px-4 py-2 border-b border-border bg-card/80 backdrop-blur-sm">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Tradução — {documento?.target_language?.toUpperCase()} · Clique para editar
              </p>
            </div>

            <div className="p-4 space-y-3">
              {chunks.map((chunk) => {
                const isSaving = saving === chunk.id;
                const isSaved  = savedIds.has(chunk.id);
                const isEdited = editando[chunk.id] !== (chunk.texto_final_revisado ?? chunk.texto_traduzido_ia ?? "");

                return (
                  <div
                    key={chunk.id}
                    className={cn(
                      "border rounded-xl p-4 transition-all duration-200",
                      isSaved
                        ? "border-green-500/50 bg-green-50/50 dark:bg-green-900/10"
                        : isEdited
                        ? "border-primary/50 bg-primary/5"
                        : "border-border bg-card"
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-muted-foreground font-mono">
                        #{chunk.chunk_index + 1}
                        {chunk.status === "revisado" && (
                          <span className="ml-2 text-green-600 font-semibold">✓ revisado</span>
                        )}
                      </span>

                      <button
                        id={`btn-salvar-${chunk.id}`}
                        onClick={() => salvarChunk(chunk.id)}
                        disabled={isSaving || !isEdited}
                        className={cn(
                          "flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg transition-all font-medium",
                          isSaved
                            ? "bg-green-500 text-white"
                            : isEdited
                            ? "text-white hover:brightness-110"
                            : "bg-muted text-muted-foreground cursor-default",
                        )}
                        style={isEdited && !isSaved ? { background: "oklch(0.6397 0.1720 36.4421)" } : {}}
                      >
                        {isSaving ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : isSaved ? (
                          <Check className="w-3 h-3" />
                        ) : (
                          <Save className="w-3 h-3" />
                        )}
                        {isSaved ? "Salvo!" : "Salvar"}
                      </button>
                    </div>

                    <textarea
                      id={`textarea-chunk-${chunk.id}`}
                      value={editando[chunk.id] ?? ""}
                      onChange={(e) =>
                        setEditando((prev) => ({ ...prev, [chunk.id]: e.target.value }))
                      }
                      rows={Math.max(3, Math.ceil((editando[chunk.id]?.length ?? 0) / 60))}
                      className={cn(
                        "w-full resize-none text-sm text-foreground leading-relaxed",
                        "bg-transparent border-none outline-none",
                        "placeholder:text-muted-foreground",
                      )}
                      placeholder="Tradução ainda não disponível..."
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Modal Glossário ── */}
      {addTerm.show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-foreground text-lg">Adicionar ao Glossário</h3>
              <button onClick={() => setAddTerm({ show: false, original: "", traducao: "" })}>
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-foreground block mb-1">Termo Original</label>
                <input
                  id="glossario-termo-original"
                  type="text"
                  value={addTerm.original}
                  onChange={(e) => setAddTerm((s) => ({ ...s, original: e.target.value }))}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="ex: Spindle"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground block mb-1">Tradução PT</label>
                <input
                  id="glossario-termo-traducao"
                  type="text"
                  value={addTerm.traducao}
                  onChange={(e) => setAddTerm((s) => ({ ...s, traducao: e.target.value }))}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-input border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="ex: Fuso"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              <button
                onClick={() => setAddTerm({ show: false, original: "", traducao: "" })}
                className="flex-1 px-4 py-2 rounded-xl border border-border text-sm text-foreground hover:bg-accent transition-colors"
              >
                Cancelar
              </button>
              <button
                id="btn-confirmar-glossario"
                onClick={handleAddTerm}
                className="flex-1 px-4 py-2 rounded-xl text-sm text-white font-semibold transition-all hover:brightness-110"
                style={{ background: "oklch(0.6397 0.1720 36.4421)" }}
              >
                <Plus className="w-4 h-4 inline mr-1" />
                Adicionar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal Exportação ── */}
      {showExport && documentoId && (
        <ExportModal
          documentoId={documentoId}
          nomeDocumento={documento?.title ?? "manual"}
          onClose={() => setShowExport(false)}
        />
      )}
    </div>
  );
}
