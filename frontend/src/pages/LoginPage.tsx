import React, { useState } from "react";
import { supabase } from "@/lib/supabase";
import { Eye, EyeOff, Loader2, BookOpen, Lock, Mail, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const SUPER_ADMIN_EMAIL = "eriklima.me@gmail.com";

export default function LoginPage() {
  const [email, setEmail] = useState(SUPER_ADMIN_EMAIL);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (authError) {
        setError(
          authError.message === "Invalid login credentials"
            ? "E-mail ou senha incorretos. Verifique suas credenciais."
            : authError.message
        );
        return;
      }

      if (data.user) {
        setSuccess(true);
        // Redirecionamento futuro: window.location.href = "/dashboard"
      }
    } catch {
      setError("Erro inesperado ao autenticar. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-background">
      {/* ─── Left Panel — Brand ─────────────────────────────────────── */}
      <div
        className="hidden lg:flex flex-col justify-between w-1/2 p-12 relative overflow-hidden"
        style={{
          background:
            "linear-gradient(135deg, oklch(0.6397 0.1720 36.4421) 0%, oklch(0.55 0.20 30) 60%, oklch(0.45 0.18 280) 100%)",
        }}
      >
        {/* Decorative circles */}
        <div
          className="absolute -top-32 -right-32 w-96 h-96 rounded-full opacity-20"
          style={{ background: "oklch(1 0 0 / 0.15)" }}
        />
        <div
          className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full opacity-10"
          style={{ background: "oklch(1 0 0 / 0.1)" }}
        />

        {/* Logo / brand */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="bg-white/20 backdrop-blur-sm rounded-2xl p-3">
            <BookOpen className="w-8 h-8 text-white" strokeWidth={1.5} />
          </div>
          <div>
            <p className="text-white/70 text-sm font-medium tracking-widest uppercase">
              TransformaFuturo
            </p>
            <h1 className="text-white text-2xl font-bold leading-tight">
              Tradutor Técnico
            </h1>
          </div>
        </div>

        {/* Hero text */}
        <div className="relative z-10">
          <h2 className="text-white text-4xl font-bold leading-snug mb-4">
            Traduza manuais<br />
            industriais com<br />
            <span className="text-white/80">precisão cirúrgica.</span>
          </h2>
          <p className="text-white/70 text-lg max-w-sm leading-relaxed">
            Inteligência artificial com glossário personalizado por empresa.
            Preservação total de diagramas CAD/CAM.
          </p>
        </div>

        {/* Feature pills */}
        <div className="relative z-10 flex flex-wrap gap-2">
          {["Multi-empresa", "IA + Glossário", "Export PDF/MD", "OCR Avançado"].map(
            (feat) => (
              <span
                key={feat}
                className="bg-white/15 backdrop-blur-sm text-white text-sm px-4 py-1.5 rounded-full border border-white/20"
              >
                {feat}
              </span>
            )
          )}
        </div>
      </div>

      {/* ─── Right Panel — Login Form ────────────────────────────────── */}
      <div className="flex flex-1 items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          {/* Mobile brand */}
          <div className="flex lg:hidden items-center gap-3 mb-10 justify-center">
            <div
              className="rounded-2xl p-3"
              style={{ background: "oklch(0.6397 0.1720 36.4421)" }}
            >
              <BookOpen className="w-7 h-7 text-white" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-muted-foreground text-xs tracking-widest uppercase">
                TransformaFuturo
              </p>
              <h1 className="text-foreground text-xl font-bold">Tradutor Técnico</h1>
            </div>
          </div>

          {/* Card */}
          <div className="bg-card border border-border rounded-2xl shadow-xl shadow-black/5 p-8">
            {/* Header */}
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-1">
                <ShieldCheck
                  className="w-5 h-5"
                  style={{ color: "oklch(0.6397 0.1720 36.4421)" }}
                />
                <span
                  className="text-xs font-semibold uppercase tracking-widest"
                  style={{ color: "oklch(0.6397 0.1720 36.4421)" }}
                >
                  Super Admin
                </span>
              </div>
              <h2 className="text-2xl font-bold text-foreground">Bem-vindo de volta</h2>
              <p className="text-muted-foreground text-sm mt-1">
                Entre com suas credenciais para acessar o painel.
              </p>
            </div>

            {/* Success state */}
            {success ? (
              <div className="flex flex-col items-center gap-4 py-8 text-center">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center"
                  style={{ background: "oklch(0.6397 0.1720 36.4421 / 0.12)" }}
                >
                  <ShieldCheck
                    className="w-8 h-8"
                    style={{ color: "oklch(0.6397 0.1720 36.4421)" }}
                  />
                </div>
                <div>
                  <p className="text-foreground font-semibold text-lg">
                    Autenticado com sucesso!
                  </p>
                  <p className="text-muted-foreground text-sm mt-1">
                    Redirecionando para o painel...
                  </p>
                </div>
              </div>
            ) : (
              <form onSubmit={handleLogin} className="space-y-5" id="login-form">
                {/* Email */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="login-email"
                    className="text-sm font-medium text-foreground"
                  >
                    E-mail
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                    <input
                      id="login-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      disabled={loading}
                      className={cn(
                        "w-full pl-10 pr-4 py-2.5 rounded-lg text-sm",
                        "bg-input border border-border",
                        "text-foreground placeholder:text-muted-foreground",
                        "focus:outline-none focus:ring-2 focus:ring-ring",
                        "transition-all duration-200",
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                      )}
                      placeholder="admin@empresa.com.br"
                    />
                  </div>
                </div>

                {/* Password */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="login-password"
                    className="text-sm font-medium text-foreground"
                  >
                    Senha
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                    <input
                      id="login-password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      disabled={loading}
                      className={cn(
                        "w-full pl-10 pr-12 py-2.5 rounded-lg text-sm",
                        "bg-input border border-border",
                        "text-foreground placeholder:text-muted-foreground",
                        "focus:outline-none focus:ring-2 focus:ring-ring",
                        "transition-all duration-200",
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                      )}
                      placeholder="••••••••••"
                    />
                    <button
                      type="button"
                      id="toggle-password-visibility"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      tabIndex={-1}
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <div
                    id="login-error-message"
                    className="flex items-start gap-2 p-3 rounded-lg border text-sm"
                    style={{
                      background: "oklch(0.6368 0.2078 25.3313 / 0.08)",
                      borderColor: "oklch(0.6368 0.2078 25.3313 / 0.3)",
                      color: "oklch(0.5 0.18 25)",
                    }}
                  >
                    <span className="shrink-0 mt-0.5">⚠️</span>
                    <span>{error}</span>
                  </div>
                )}

                {/* Submit */}
                <button
                  id="login-submit-button"
                  type="submit"
                  disabled={loading || !email || !password}
                  className={cn(
                    "w-full flex items-center justify-center gap-2",
                    "py-2.5 px-4 rounded-lg text-sm font-semibold",
                    "text-white transition-all duration-200",
                    "disabled:opacity-50 disabled:cursor-not-allowed",
                    "hover:brightness-110 active:scale-[0.98]"
                  )}
                  style={{ background: "oklch(0.6397 0.1720 36.4421)" }}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Autenticando...
                    </>
                  ) : (
                    "Entrar no Painel"
                  )}
                </button>
              </form>
            )}
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-muted-foreground mt-6">
            © {new Date().getFullYear()} TransformaFuturo · Tradutor Técnico SaaS
          </p>
        </div>
      </div>
    </div>
  );
}
