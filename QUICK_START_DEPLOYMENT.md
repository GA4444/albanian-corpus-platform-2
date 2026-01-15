# ⚡ Quick Start Deployment Guide

Ky është një guide i shkurtër për deployment të shpejtë. Për instruksione të detajuara, shiko [DEPLOYMENT.md](./DEPLOYMENT.md).

## 🎯 Opsioni 1: Render + Vercel (Rekomanduar)

### Backend (5 minuta)

1. **Shko në [Render](https://render.com)** dhe krijo account
2. **New + → Web Service** → Lidh GitHub repo
3. **Settings:**
   - Name: `alblingo-backend`
   - Root Directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **New + → PostgreSQL** → Krijo database (Free tier)
5. **Environment Variables:**
   ```
   DATABASE_URL=<auto nga PostgreSQL>
   FRONTEND_URL=<do ta vendosësh pas frontend>
   PYTHONUNBUFFERED=1
   ```
6. **Deploy** → Kopjo URL (p.sh. `https://alblingo-backend.onrender.com`)

### Frontend (3 minuta)

1. **Shko në [Vercel](https://vercel.com)** dhe krijo account
2. **Add New → Project** → Import GitHub repo
3. **Settings:**
   - Framework: Vite
   - Root Directory: `frontend`
   - Build: `npm run build`
   - Output: `dist`
4. **Environment Variables:**
   ```
   VITE_API_BASE_URL=https://alblingo-backend.onrender.com
   ```
5. **Deploy** → Kopjo URL (p.sh. `https://alblingo-frontend.vercel.app`)

### Final Step

1. **Shko te Render → Backend → Environment**
2. **Update `FRONTEND_URL`** me URL-n e Vercel
3. **Restart service**

✅ **Gati!** Platforma është live!

---

## 🎯 Opsioni 2: Supabase + Render + Vercel (Falas përgjithmonë)

### Database (Supabase - 2 minuta)

1. **Shko në [Supabase](https://supabase.com)** → New Project
2. **Settings → Database** → Kopjo Connection String
3. **Përdor në Render** si `DATABASE_URL`

### Backend & Frontend

Njejtë si Opsioni 1, por përdor Supabase connection string në vend të Render PostgreSQL.

---

## 📝 Checklist

- [ ] Backend deployed në Render
- [ ] Database krijuar (Render PostgreSQL ose Supabase)
- [ ] Frontend deployed në Vercel
- [ ] `FRONTEND_URL` vendosur në backend
- [ ] `VITE_API_BASE_URL` vendosur në frontend
- [ ] Test API: `curl https://your-backend.onrender.com/health`
- [ ] Test frontend në browser

---

## ⚠️ Shënime të Rëndësishme

1. **Render Free tier "flet" pas 15 min** → Përgjigja e parë mund të marrë 30-60 sekonda
2. **Database migrations** duhen ekzekutuar manualisht (shiko DEPLOYMENT.md)
3. **Seed data** për ushtrimet: `POST /api/seed-albanian-corpus`

---

## 🆘 Probleme?

- **Backend nuk starton?** → Check logs në Render
- **CORS error?** → Verifikoj `FRONTEND_URL` në backend
- **Frontend nuk lidhet?** → Verifikoj `VITE_API_BASE_URL`
- **Database error?** → Check connection string format

Shiko [DEPLOYMENT.md](./DEPLOYMENT.md) për troubleshooting të detajuar.
