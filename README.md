# 1Health Pharmacy Chatbot

A web-based AI pharmacy assistant for **1Health Pharmacy** — a floating chat
widget that lets patients order medicines, upload prescriptions (read by GPT-4o
Vision), choose pickup or home delivery, and pay online or via COD. It shares
the same Supabase database as the existing Telegram bot.

## Tech stack

| Layer | Tech |
|-------|------|
| Backend | Python, FastAPI, WebSocket |
| AI agent | LangGraph + LangChain, OpenAI GPT-4o / GPT-4o-mini |
| Database | Supabase (PostgreSQL) |
| Prescription OCR | OpenAI GPT-4o Vision |
| Payments | Razorpay (test mode) |
| Frontend | React + TypeScript + Vite + Tailwind CSS |

## Repository layout

```
backend/          FastAPI app
  agent/          LangGraph state machine + conversation nodes
  api/            WebSocket chat, admin REST, webhooks (razorpay, supabase)
  services/       Supabase, storage, matching, razorpay, pub/sub, messages
  main.py         app entrypoint
frontend/         React chat widget + demo storefront
```

## Local setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
copy .env.example .env         # then fill in real keys
python -m uvicorn main:app --reload --port 8000
```

Required env vars (see `backend/.env.example`): `OPENAI_API_KEY`,
`SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (service_role **JWT** key, `eyJ...`).
Razorpay + webhook secrets are optional (needed only for online payment).

### Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

Set `VITE_API_BASE` to the backend URL in production (defaults to
`http://localhost:8000` in dev).

## Deployment

- **Frontend** → Vercel (static Vite build).
- **Backend** → an always-on host that supports WebSockets (Render / Railway /
  Fly.io). Vercel serverless does **not** support the persistent WebSocket +
  in-process pub/sub this app uses.
- Point the Supabase order-status Database Webhook and the Razorpay webhook at
  the deployed backend URL.

## Security

Never commit `backend/.env` — it holds live API keys (already in `.gitignore`).
Use the host's environment-variable settings in production.
