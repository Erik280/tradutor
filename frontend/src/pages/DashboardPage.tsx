import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Upload, FileText, CheckCircle2, Clock, AlertCircle,
  Loader2, Building2, ChevronRight, RefreshCw, LogOut,
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const SUPER_ADMIN_EMAIL = "eriklima.me@gmail.com";

type DocStatus = "uploaded"|"processing"|"extracted"|"translating"|"translated"|"reviewing"|"approved"|"exported"|"error";

interface Documento {
  id: string;
  title: string;
  status: DocStatus;
  total_pages: number | null;
  source_language: string;
  target_language: string;
  created_at: string;
  progresso?: { percentual: number; total: number; traduzido: number };
}

interface Empresa {
  id: string;
  nome_comercial: string;
}

const STATUS_CONFIG: Record<DocStatus, { label: string; color: string; icon: React.ReactNode }> = {
  uploaded:     { label: "Recebido",       color: "text-blue-500",   icon: <FileText className="w-4 h-4" /> },
  processing:   { label: "Processando",    color: "text-yellow-500", icon: <Loader2 className="w-4 h-4 animate-spin" /> },
  extracted:    { label: "Extraído",       color: "text-yellow-500", icon: <Loader2 className="w-4 h-4 animate-spin" /> },
  translating:  { label: "Traduzindo...",  color: "text-primary",    icon: <Loader2 className="w-4 h-4 animate-spin" /> },
  translated:   { label: "Traduzido",      color: "text-green-600",  icon: <CheckCircle2 className="w-4 h-4" /> },
  reviewing:    { label: "Em Revisão",     color: "text-orange-500", icon: <Clock className="w-4 h-4" /> },
  approved:     { label: "Aprovado",       color: "text-green-600",  icon: <CheckCircle2 className="w-4 h-4" /> },
  exported:     { label: "Exportado",      color: "text-green-600",  icon: <CheckCircle2 className="w-4 h-4" /> },
  error:        { label: "Erro",           color: "text-red-500",    icon: <AlertCircle className="w-4 h-4" /> },
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const fileRef  = useRef<HTMLInputElement>(null);

  const [userEmail,   setUserEmail]   = useState("");
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [empresas,    setEmpresas]    = useState<Empresa[]>([]);
  const [empresaSel,  setEmpresaSel]  = useState<string>("");
  const [documentos,  setDocumentos]  = useState<Documento[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [uploading,   setUploading]   = useState(false);
  const [dragOver,    setDragOver]    = useState(false);

  // ── Auth ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      const { data } = await supabase.auth.getUser();
      const email = data.user?.email ?? "";
      setUserEmail(email);
      setIsSuperAdmin(email === SUPER_ADMIN_EMAIL);

      if (email === SUPER_ADMIN_EMAIL) {
        // Super Admin: carregar lista de empresas
        const { data: companies } = await supabase
          .from("companies")
          .select("id,name")
          .order("name");
        setEmpresas((companies ?? []).map((c: any) => ({ id: c.id, nome_comercial: c.name })));
      }

      await carregarDocumentos();
    })();
  }, []);

  useEffect(() => {
    carregarDocumentos();
  }, [empresaSel]);

  async function carregarDocumentos() {
    setLoading(true);
    try {
      const docs = await api.listarDocumentos(empresaSel || undefined);
      setDocumentos(docs);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  // ── Upload ────────────────────────────────────────────────────────────────
  async function handleUpload(file: File) {
    if (!file || !file.name.endsWith(".pdf")) {
      alert("Apenas arquivos PDF são aceitos.");
      return;
    }
    setUploading(true);
    try {
      await api.uploadDocumento(file);
      await carregarDocumentos();
    } catch (e: any) {
      alert(`Erro no upload: ${e.message}`);
    } finally {
      setUploading(false);
    }
  }

  // ── Logout ────────────────────────────────────────────────────────────────
  async function handleLogout() {
    await supabase.auth.signOut();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-background">
      {/* ── Navbar ── */}
      <nav className="border-b border-border bg-card px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="rounded-xl p-2"
            style={{ background: "oklch(0.6397 0.1720 36.4421)" }}
          >
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-foreground text-lg leading-tight">Tradutor Técnico</h1>
            <p className="text-xs text-muted-foreground">TransformaFuturo · SaaS</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Seletor de empresa — apenas super admin */}
          {isSuperAdmin && empresas.length > 0 && (
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-muted-foreground" />
              <select
                id="empresa-select"
                value={empresaSel}
                onChange={(e) => setEmpresaSel(e.target.value)}
                className="text-sm bg-input border border-border rounded-lg px-3 py-1.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Todas as empresas</option>
                {empresas.map((e) => (
                  <option key={e.id} value={e.id}>{e.nome_comercial}</option>
                ))}
              </select>
            </div>
          )}

          <span className="text-xs text-muted-foreground hidden sm:block">{userEmail}</span>

          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </button>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* ── Upload Zone ── */}
        <div
          id="upload-zone"
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file) handleUpload(file);
          }}
          onClick={() => !uploading && fileRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200 mb-8",
            dragOver
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50 hover:bg-accent/30",
            uploading && "opacity-50 cursor-not-allowed"
          )}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
          />

          {uploading ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-10 h-10 animate-spin" style={{ color: "oklch(0.6397 0.1720 36.4421)" }} />
              <p className="text-foreground font-medium">Enviando e iniciando tradução...</p>
              <p className="text-sm text-muted-foreground">Isso pode demorar alguns instantes</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center"
                style={{ background: "oklch(0.6397 0.1720 36.4421 / 0.1)" }}
              >
                <Upload className="w-7 h-7" style={{ color: "oklch(0.6397 0.1720 36.4421)" }} />
              </div>
              <div>
                <p className="text-foreground font-semibold">Solte o PDF aqui ou clique para selecionar</p>
                <p className="text-sm text-muted-foreground mt-1">PDF até 100 MB · Manuais técnicos, CAD/CAM, Engenharia</p>
              </div>
            </div>
          )}
        </div>

        {/* ── Header Lista ── */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-foreground">Manuais</h2>
          <button
            onClick={carregarDocumentos}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
            Atualizar
          </button>
        </div>

        {/* ── Lista de Documentos ── */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : documentos.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>Nenhum manual encontrado. Faça o upload do primeiro PDF!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {documentos.map((doc) => {
              const cfg = STATUS_CONFIG[doc.status] ?? STATUS_CONFIG.error;
              const pct = doc.progresso?.percentual ?? 0;
              const canReview = ["translated", "reviewing", "approved"].includes(doc.status);

              return (
                <div
                  key={doc.id}
                  className="bg-card border border-border rounded-2xl p-5 flex items-center gap-4 hover:border-primary/30 transition-all duration-200"
                >
                  {/* Ícone */}
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                    style={{ background: "oklch(0.6397 0.1720 36.4421 / 0.08)" }}
                  >
                    <FileText className="w-5 h-5" style={{ color: "oklch(0.6397 0.1720 36.4421)" }} />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate">{doc.title}</p>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                      <span className={cn("flex items-center gap-1 text-xs font-medium", cfg.color)}>
                        {cfg.icon}
                        {cfg.label}
                      </span>
                      {doc.total_pages && (
                        <span className="text-xs text-muted-foreground">{doc.total_pages} páginas</span>
                      )}
                      <span className="text-xs text-muted-foreground uppercase">
                        {doc.source_language} → {doc.target_language}
                      </span>
                    </div>

                    {/* Barra de progresso */}
                    {pct > 0 && (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{
                              width: `${pct}%`,
                              background: "oklch(0.6397 0.1720 36.4421)",
                            }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground tabular-nums">{pct}%</span>
                      </div>
                    )}
                  </div>

                  {/* Botão Revisar */}
                  {canReview && (
                    <button
                      id={`btn-revisar-${doc.id}`}
                      onClick={() => navigate(`/revisao/${doc.id}`)}
                      className="flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-xl text-white transition-all hover:brightness-110 shrink-0"
                      style={{ background: "oklch(0.6397 0.1720 36.4421)" }}
                    >
                      Revisar
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
