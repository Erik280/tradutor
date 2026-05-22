# 🔧 Tradutor Técnico — SaaS Multi-tenant

> Plataforma de tradução de manuais técnicos industriais com IA, glossário personalizado e exportação preservando diagramas CAD/CAM.

**Domínio:** `tradutor.transformafuturo.com.br`

---

## 🏗️ Arquitetura

```
tradutor-pdf/
├── docker-compose.yml        # Stack do Portainer
├── .env.example              # Template de variáveis
├── backend/
│   ├── Dockerfile            # Python 3.12 multi-stage
│   ├── requirements.txt
│   └── app/
│       └── main.py           # FastAPI + /health + CORS
└── frontend/
    ├── Dockerfile            # Node build → Nginx runtime
    ├── nginx.conf            # SPA routing + gzip
    ├── vite.config.ts
    ├── package.json
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css         # Tema Tangerine (OKLCH)
        ├── lib/
        │   ├── supabase.ts
        │   └── utils.ts
        └── pages/
            └── LoginPage.tsx # Tela de login Super Admin
```

## 🚀 Rodando Localmente

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## 🐳 Deploy via Portainer (Stack)

1. Configure o repositório GitHub no Portainer.
2. Copie `.env.example` → `.env` e preencha as variáveis.
3. O Portainer lerá o `docker-compose.yml` diretamente da branch `main`.

## 🔑 Variáveis de Ambiente

| Variável | Descrição |
|---|---|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_ANON_KEY` | Chave pública (anon) |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave secreta (service role) |
| `ALLOWED_ORIGINS` | Origens CORS permitidas |
| `ENVIRONMENT` | `production` ou `development` |
