import { useState } from "react";
import { X, FileText, FileCode2, Loader2, Download } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  documentoId: string;
  nomeDocumento: string;
  onClose: () => void;
}

type Mode = "pdf" | "markdown";

export default function ExportModal({ documentoId, nomeDocumento, onClose }: Props) {
  const [mode,           setMode]           = useState<Mode>("pdf");
  const [quebraManual,   setQuebraManual]   = useState(false);
  const [fontOffset,     setFontOffset]     = useState<number>(-2.0);
  const [loading,        setLoading]        = useState(false);
  const [done,           setDone]           = useState(false);
  const [error,          setError]          = useState<string | null>(null);

  async function handleExport() {
    setLoading(true);
    setError(null);
    try {
      const blob = await api.exportarDocumento(documentoId, mode === "pdf", quebraManual, fontOffset);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = mode === "pdf"
        ? `${nomeDocumento}_traduzido.pdf`
        : `${nomeDocumento}_traduzido.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setDone(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-card border border-border rounded-2xl p-6 w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="font-bold text-foreground text-xl">Exportar Manual</h3>
            <p className="text-sm text-muted-foreground mt-0.5">
              Escolha o formato de saída do documento traduzido
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Opções */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {/* PDF com Imagens */}
          <button
            id="export-option-pdf"
            onClick={() => setMode("pdf")}
            className={cn(
              "flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all duration-200 text-left",
              mode === "pdf"
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/40 hover:bg-accent/30"
            )}
          >
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{
                background: mode === "pdf"
                  ? "oklch(0.6397 0.1720 36.4421 / 0.15)"
                  : "oklch(0.9119 0.0222 243.8174)",
              }}
            >
              <FileText
                className="w-6 h-6"
                style={{ color: mode === "pdf" ? "oklch(0.6397 0.1720 36.4421)" : "#6b7280" }}
              />
            </div>
            <div>
              <p className="font-semibold text-sm text-foreground">PDF com Imagens</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Layout original preservado. Diagramas CAD/CAM intactos. Texto injetado por overlay.
              </p>
            </div>
            <div
              className="w-full text-center text-xs font-medium py-1 rounded-lg"
              style={{
                background: mode === "pdf"
                  ? "oklch(0.6397 0.1720 36.4421)"
                  : "oklch(0.9022 0.0052 247.8822)",
                color: mode === "pdf" ? "white" : "#6b7280",
              }}
            >
              Recomendado
            </div>
          </button>

          {/* Markdown / Texto Limpo */}
          <button
            id="export-option-markdown"
            onClick={() => setMode("markdown")}
            className={cn(
              "flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all duration-200 text-left",
              mode === "markdown"
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/40 hover:bg-accent/30"
            )}
          >
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{
                background: mode === "markdown"
                  ? "oklch(0.6397 0.1720 36.4421 / 0.15)"
                  : "oklch(0.9119 0.0222 243.8174)",
              }}
            >
              <FileCode2
                className="w-6 h-6"
                style={{ color: mode === "markdown" ? "oklch(0.6397 0.1720 36.4421)" : "#6b7280" }}
              />
            </div>
            <div>
              <p className="font-semibold text-sm text-foreground">Texto Limpo (.md)</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Somente o texto traduzido em Markdown estruturado. Sem imagens.
              </p>
            </div>
            <div
              className="w-full text-center text-xs font-medium py-1 rounded-lg"
              style={{
                background: mode === "markdown"
                  ? "oklch(0.6397 0.1720 36.4421)"
                  : "oklch(0.9022 0.0052 247.8822)",
                color: mode === "markdown" ? "white" : "#6b7280",
              }}
            >
              Texto Corrido
            </div>
          </button>
        </div>

        {/* Checkbox Quebra Manual e Ajuste de Fonte (Apenas para PDF) */}
        {mode === "pdf" && (
          <div className="mb-5 space-y-3">
            <label className="flex items-start gap-3 p-3 border border-border rounded-xl cursor-pointer hover:bg-accent/50 transition-colors">
              <input
                type="checkbox"
                checked={quebraManual}
                onChange={(e) => setQuebraManual(e.target.checked)}
                className="mt-0.5 rounded text-primary focus:ring-primary w-4 h-4"
              />
              <div>
                <p className="text-sm font-medium text-foreground">Desativar quebra automática de linha</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Marque isto se um texto curto estiver quebrando a linha no PDF (ideal para rótulos curtos que têm espaço sobrando à direita). O PDF vai respeitar apenas os ENTERS que você deu.
                </p>
              </div>
            </label>

            <div className="flex items-center justify-between p-3 border border-border rounded-xl">
              <div>
                <p className="text-sm font-medium text-foreground">Ajuste Global de Fonte</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Recomendado -2 para compensar o tamanho do PT-BR.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setFontOffset((p) => p - 1)}
                  className="w-8 h-8 flex items-center justify-center rounded bg-accent text-foreground hover:brightness-95"
                >-</button>
                <span className="w-8 text-center text-sm font-mono">{fontOffset > 0 ? `+${fontOffset}` : fontOffset}px</span>
                <button
                  onClick={() => setFontOffset((p) => p + 1)}
                  className="w-8 h-8 flex items-center justify-center rounded bg-accent text-foreground hover:brightness-95"
                >+</button>
              </div>
            </div>
          </div>
        )}

        {/* Info box */}
        <div
          className="rounded-xl p-3 mb-5 text-sm"
          style={{
            background: "oklch(0.6397 0.1720 36.4421 / 0.08)",
            border: "1px solid oklch(0.6397 0.1720 36.4421 / 0.2)",
            color: "oklch(0.4 0.12 36)",
          }}
        >
          {mode === "pdf" ? (
            <p>📄 O PDF gerado preserva 100% dos diagramas e vetores do original. O texto traduzido é injetado como camada digital — completamente pesquisável com Ctrl+F.</p>
          ) : (
            <p>📝 O Markdown exportado organiza o conteúdo por página com cabeçalhos e separadores. Ideal para revisão em editores de texto ou sistemas de documentação.</p>
          )}
        </div>

        {/* Erro */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 mb-4 text-sm text-red-700">
            ⚠️ {error}
          </div>
        )}

        {/* Botões */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-xl border border-border text-sm text-foreground hover:bg-accent transition-colors"
          >
            Cancelar
          </button>
          <button
            id="btn-confirmar-exportar"
            onClick={handleExport}
            disabled={loading || done}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all",
              done ? "bg-green-500" : "hover:brightness-110",
              loading && "opacity-80"
            )}
            style={!done ? { background: "oklch(0.6397 0.1720 36.4421)" } : {}}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Gerando...
              </>
            ) : done ? (
              <>✓ Download Iniciado!</>
            ) : (
              <>
                <Download className="w-4 h-4" />
                {mode === "pdf" ? "Baixar PDF" : "Baixar .md"}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
