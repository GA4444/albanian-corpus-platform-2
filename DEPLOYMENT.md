# 🚀 Deployment Guide - ALBLingo Platform

Ky dokument përmban instruksione të detajuara për deployment të platformës ALBLingo në shërbime falas.

## 📋 Përmbajtja

1. [Kërkesat](#kërkesat)
2. [Deployment i Backend (Render)](#deployment-i-backend-render)
3. [Deployment i Frontend (Vercel)](#deployment-i-frontend-vercel)
4. [Konfigurim i Database](#konfigurim-i-database)
5. [Environment Variables](#environment-variables)
6. [Troubleshooting](#troubleshooting)

---

## Kërkesat

- Account në [Render](https://render.com) (falas)
- Account në [Vercel](https://vercel.com) (falas) ose [Netlify](https://netlify.com) (falas)
- Account në [Supabase](https://supabase.com) (falas) për PostgreSQL ose përdor Render PostgreSQL
- GitHub repository me të gjithë kodin

---

## Deployment i Backend (Render)

### Hapi 1: Përgatitja e Repository

1. Sigurohu që të gjitha ndryshimet janë commit dhe push në GitHub:
```bash
git add .
git commit -m "Add deployment configuration"
git push origin main
```

### Hapi 2: Krijo Web Service në Render

1. Shko në [Render Dashboard](https://dashboard.render.com)
2. Kliko "New +" → "Web Service"
3. Lidh repository-n tënd GitHub
4. Zgjidh repository-n `albanian-corpus-platform-2`

### Hapi 3: Konfigurim i Service

**Settings:**
- **Name:** `alblingo-backend`
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory:** `backend`

**Environment Variables:**
```
DATABASE_URL=<do të vendoset automatikisht nga PostgreSQL>
FRONTEND_URL=https://your-frontend.vercel.app
PYTHONUNBUFFERED=1
TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
OPENAI_API_KEY=<opsionale - për features të avancuara>
ANTHROPIC_API_KEY=<opsionale>
AZURE_SPEECH_KEY=<opsionale>
AZURE_SPEECH_REGION=<opsionale>
```

### Hapi 4: Krijo PostgreSQL Database

1. Në Render Dashboard, kliko "New +" → "PostgreSQL"
2. Emër: `alblingo-db`
3. Plan: **Free** (90 ditë falas, pastaj $7/mujor)
4. Kopjo **Internal Database URL** dhe vendose në `DATABASE_URL` environment variable

**Ose përdor Supabase (falas përgjithmonë):**
1. Krijo projekt në [Supabase](https://supabase.com)
2. Shko te Settings → Database
3. Kopjo **Connection String** (URI format)
4. Vendose në `DATABASE_URL`

### Hapi 5: Deploy

1. Kliko "Create Web Service"
2. Render do të fillojë build dhe deploy
3. Pas 5-10 minuta, do të marrësh URL: `https://alblingo-backend.onrender.com`

**⚠️ Shënim:** Në planin falas, service-i do të "fjet" pas 15 minutash pa aktivitet. Përgjigja e parë mund të marrë 30-60 sekonda.

---

## Deployment i Frontend (Vercel)

### Hapi 1: Import Project

1. Shko në [Vercel Dashboard](https://vercel.com/dashboard)
2. Kliko "Add New..." → "Project"
3. Import repository-n nga GitHub
4. Zgjidh `albanian-corpus-platform-2`

### Hapi 2: Konfigurim

**Project Settings:**
- **Framework Preset:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install`

**Environment Variables:**
```
VITE_API_BASE_URL=https://alblingo-backend.onrender.com
```

### Hapi 3: Deploy

1. Kliko "Deploy"
2. Pas 2-3 minuta, do të marrësh URL: `https://alblingo-frontend.vercel.app`

### Hapi 4: Update Backend CORS

1. Shko te Render Dashboard → Backend Service → Environment
2. Shto/update `FRONTEND_URL` me URL-n e Vercel:
```
FRONTEND_URL=https://alblingo-frontend.vercel.app
```
3. Restart service

---

## Konfigurim i Database

### Migrimi i Schema

Pas deployment, duhet të ekzekutosh migrimet e database:

1. **Lokal (për test):**
```bash
cd backend
python migrate_user_profile.py
python migrate_gamification.py
python scripts/init_gamification.py
```

2. **Në Production (Render):**
- Ose përdor Render Shell për të ekzekutuar migrimet
- Ose shto një endpoint admin për migrim (jo në production!)

### Seed i të Dhënave

Për të seed-uar ushtrimet:
```bash
# Në Render Shell ose lokal me DATABASE_URL production
curl -X POST https://alblingo-backend.onrender.com/api/seed-albanian-corpus
```

---

## Environment Variables

### Backend (Render)

| Variable | Vlera | Opsionale |
|----------|-------|-----------|
| `DATABASE_URL` | PostgreSQL connection string | ❌ |
| `FRONTEND_URL` | URL e frontend (Vercel) | ❌ |
| `PYTHONUNBUFFERED` | `1` | ❌ |
| `OPENAI_API_KEY` | OpenAI API key | ✅ |
| `ANTHROPIC_API_KEY` | Anthropic API key | ✅ |
| `AZURE_SPEECH_KEY` | Azure Speech key | ✅ |
| `AZURE_SPEECH_REGION` | Azure region | ✅ |

### Frontend (Vercel)

| Variable | Vlera | Opsionale |
|----------|-------|-----------|
| `VITE_API_BASE_URL` | Backend URL (Render) | ❌ |

---

## Troubleshooting

### Backend nuk starton

1. **Check logs në Render Dashboard**
2. **Verifikoj që `requirements.txt` është i plotë**
3. **Kontrolloj që `DATABASE_URL` është i vendosur**
4. **Verifikoj që port është `$PORT` (jo 8000 hardcoded)**

### Frontend nuk lidhet me Backend

1. **Verifikoj `VITE_API_BASE_URL` në Vercel**
2. **Kontrolloj CORS në backend (`FRONTEND_URL`)**
3. **Testoj backend URL direkt:**
```bash
curl https://alblingo-backend.onrender.com/health
```

### Database Connection Error

1. **Verifikoj `DATABASE_URL` format:**
```
postgresql://user:password@host:port/database
```
2. **Kontrolloj që database është aktiv në Render/Supabase**
3. **Testoj connection lokal me production URL**

### Build Fail në Frontend

1. **Kontrolloj që `package.json` dependencies janë të sakta**
2. **Verifikoj që `vite.config.ts` është i konfiguruar**
3. **Check build logs në Vercel**

### Slow Response (Cold Start)

- **Render Free tier:** Service "flet" pas 15 min. Përgjigja e parë mund të marrë 30-60 sekonda.
- **Zgjidhje:** Upgrade në paid plan ose përdor cron job për të mbajtur aktiv.

---

## 🔗 Links të Dobishëm

- [Render Documentation](https://render.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

## 📝 Shënime

1. **SQLite nuk rekomandohet për production** - përdor PostgreSQL
2. **Render Free tier ka limite** - 750 orë/mujor, 512 MB RAM
3. **Vercel Free tier është i mjaftueshëm** për shumicën e projekteve
4. **Database migrations** duhen ekzekutuar manualisht pas deployment
5. **Environment variables** duhen vendosur në të dy shërbimet

---

## ✅ Checklist Deployment

- [ ] Backend deployed në Render
- [ ] PostgreSQL database krijuar
- [ ] Environment variables vendosur në backend
- [ ] Frontend deployed në Vercel
- [ ] Environment variables vendosur në frontend
- [ ] CORS konfiguruar në backend
- [ ] Database migrations ekzekutuar
- [ ] Test API endpoints
- [ ] Test frontend-backend connection
- [ ] Seed initial data (ushtrimet)

---

**Për pyetje ose probleme, kontakto developer-in ose shiko dokumentacionin e shërbimeve.**
