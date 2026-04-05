# ⚡ PitchLab

**A production-ready micro-SaaS platform for web designers who sell websites to local businesses.**

Find leads → Audit their websites → Generate AI pitches → Send outreach → Close deals.

---

## What This Is

PitchLab is a complete, working SaaS platform built for solo entrepreneurs and freelancers who sell web design to local trade businesses (plumbers, electricians, roofers, landscapers, dentists, etc.).

**The workflow:**
1. Search Google Maps (or mock data) for local businesses in a niche + location
2. Automatically audit their website for speed, mobile, SEO, and design issues
3. Generate personalized AI pitches (cold email, cold call script, SMS)
4. Send outreach directly from the platform and track opens/replies
5. Manage everything with a credit-based billing system + Stripe subscriptions

---

## Tech Stack

| Layer       | Technology |
|-------------|-----------|
| Backend     | Python 3.11 + FastAPI (async) |
| Database    | SQLite (dev) / PostgreSQL (prod) |
| ORM         | SQLAlchemy 2.0 (async) |
| Auth        | JWT (python-jose) + bcrypt |
| AI          | Groq (primary) / Anthropic (fallback) / Mock |
| Lead source | Google Places API / Mock data |
| Payments    | Stripe Subscriptions |
| Email       | SMTP (Gmail or any provider) |
| SMS         | Mock (Twilio-ready) |
| Task queue  | Celery + Redis (optional) |
| Frontend    | React 18 + Vite + React Router v6 |
| State       | Zustand |
| Styling     | Custom CSS design system (no Tailwind) |
| Deployment  | Docker Compose + Nginx |

---

## Project Structure

```
pitchlab/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py        # All settings (env vars)
│   │   │   ├── database.py      # Async SQLAlchemy engine
│   │   │   └── security.py      # JWT + bcrypt utilities
│   │   ├── models/
│   │   │   └── user.py          # ALL DB models (User, Lead, Audit, Pitch, Message, Credits)
│   │   ├── services/
│   │   │   ├── lead_finder.py   # Google Places + mock data
│   │   │   ├── audit_engine.py  # Website audit (speed/mobile/SEO/design)
│   │   │   ├── pitch_generator.py # AI pitch generation (Groq/Anthropic)
│   │   │   ├── credit_service.py  # Credit deduction + resets
│   │   │   └── messaging_service.py # Email/SMS dispatch
│   │   └── api/
│   │       ├── auth.py          # /api/auth/*
│   │       ├── leads.py         # /api/leads/*
│   │       ├── audits.py        # /api/audits/*
│   │       ├── pitches.py       # /api/pitches/*
│   │       ├── messaging.py     # /api/messaging/*
│   │       ├── credits.py       # /api/credits/*
│   │       └── billing.py       # /api/billing/*
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx             # React entry + router
│   │   ├── lib/
│   │   │   ├── api.js           # Axios instance
│   │   │   └── store.js         # Zustand stores
│   │   ├── components/
│   │   │   └── Layout.jsx       # Sidebar + nav
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx    # Stats + workflow guide
│   │   │   ├── LeadFinder.jsx   # Search UI with filters
│   │   │   ├── Leads.jsx        # Lead list/table
│   │   │   ├── LeadDetail.jsx   # Audit + Pitch + Send (core workflow)
│   │   │   ├── Messaging.jsx    # History + sequences
│   │   │   └── Billing.jsx      # Plans + credits
│   │   └── styles/
│   │       └── globals.css      # Design system CSS vars
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
│
└── docker-compose.yml
```

---

## Quick Start (Local Dev)

### Prerequisites
- Python 3.11+
- Node.js 20+
- (Optional) Redis for background tasks

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (see Configuration section below)

# Start the server
uvicorn app.main:app --reload --port 8000
```

The API will be live at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies /api to localhost:8000)
npm run dev
```

The app will be live at `http://localhost:3000`

---

## Configuration

Edit `backend/.env` — the platform works out-of-the-box with mock data, so most keys are optional for local development.

### Required for full functionality:

| Variable | Purpose | Get it from |
|----------|---------|-------------|
| `SECRET_KEY` | JWT signing key | Any long random string |
| `GROQ_API_KEY` | AI pitch generation | console.groq.com (free tier available) |
| `GOOGLE_PLACES_API_KEY` | Real lead search | console.cloud.google.com |
| `STRIPE_SECRET_KEY` | Subscriptions | dashboard.stripe.com |
| `SMTP_USER` / `SMTP_PASSWORD` | Email sending | Gmail App Password |

### Without any API keys:
- Lead search returns mock Massachusetts business data
- AI pitches use pre-written templates
- Email sending logs to console (no actual send)
- Stripe uses mock checkout flow

This means you can **demo the full product** without any external accounts.

---

## API Reference

### Auth
```
POST /api/auth/register  { email, password, full_name }
POST /api/auth/login     { email, password }
GET  /api/auth/me
```

### Leads
```
POST /api/leads/search   { location, niche, filters... }  — costs 5 credits
GET  /api/leads/          ?status=&has_website=&page=
GET  /api/leads/{id}
PATCH /api/leads/{id}/status  { status: "contacted" }
DELETE /api/leads/{id}
```

### Audits
```
POST /api/audits/{lead_id}/run   — costs 3 credits
GET  /api/audits/{lead_id}
```

### Pitches
```
POST /api/pitches/{lead_id}/generate  — costs 2 credits
GET  /api/pitches/{lead_id}
```

### Messaging
```
POST /api/messaging/send        { lead_id, channel, subject, body }  — costs 1 credit
POST /api/messaging/sequences   { lead_id, name, steps[] }
GET  /api/messaging/sequences
GET  /api/messaging/history
GET  /api/messaging/track/{id}/open  (tracking pixel)
```

### Credits
```
GET  /api/credits/balance
```

### Billing
```
GET  /api/billing/plans
POST /api/billing/create-checkout  { plan, success_url, cancel_url }
POST /api/billing/webhook           (Stripe webhook)
```

---

## Credit System

| Action | Cost |
|--------|------|
| Lead search (batch) | 5 credits |
| Website audit | 3 credits |
| AI pitch generation | 2 credits |
| Send message | 1 credit |

| Plan | Monthly Credits | Price |
|------|----------------|-------|
| Free | 25 | $0 |
| Pro  | 500 | $49/mo |

Credits reset monthly on the subscription anniversary date. Free plan users get 25 credits on signup and on the 30-day mark.

---

## AI Prompts Used Internally

The AI pitch generator in `services/pitch_generator.py` uses this system prompt:

```
You are an expert sales copywriter for a web design agency that sells websites 
to local trade businesses. Write SHORT, SPECIFIC, PERSUASIVE outreach messages.

Rules:
- Always mention 1-2 SPECIFIC problems found in the audit
- Cold email: under 100 words. Subject line: under 8 words.
- Cold call script: conversational, under 150 words
- SMS: under 60 words, very casual
- Tone: friendly, local, like a neighbor who knows websites
- End with a soft CTA (a question, not a command)
```

Then the user prompt feeds in: business name, niche, top audit issues, and the sales summary.

This produces highly specific pitches like:
> *"Hey, I was looking up plumbers in Haverhill and noticed your website has no mobile viewport tag — Chrome shows it as broken on phones. I build sites for local plumbers that rank on Google. Would a quick 10-minute call this week make sense?"*

---

## Docker Deployment

```bash
# Copy and configure env
cp backend/.env.example backend/.env
# Edit backend/.env with production values:
# - Use PostgreSQL DATABASE_URL
# - Set real STRIPE_* keys
# - Set real SMTP credentials
# - Set real GROQ_API_KEY

# Build and start everything
docker compose up --build -d

# View logs
docker compose logs -f backend

# Run database migrations (first time)
docker compose exec backend alembic upgrade head
```

The stack will be available at `http://localhost` (port 80).

---

## Production Deployment (Ubuntu VPS)

### Option 1: Docker Compose (Recommended)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone repo
git clone https://github.com/yourname/pitchlab.git
cd pitchlab

# Configure env
cp backend/.env.example backend/.env
nano backend/.env

# Start
docker compose up -d

# Set up SSL with Certbot + Nginx (optional but recommended)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Option 2: Manual (Gunicorn + Nginx)

```bash
# Backend
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Frontend (build then serve with Nginx)
cd frontend && npm run build
# Copy dist/ to /var/www/pitchlab/
# Configure Nginx to serve dist/ and proxy /api to :8000
```

### Deploy to Railway / Render

1. Push to GitHub
2. Create a new project in Railway/Render
3. Connect your backend folder as a service
4. Set all environment variables in the dashboard
5. Add a PostgreSQL database service
6. Deploy

---

## Extending PitchLab

### Add real SMS (Twilio)
In `services/messaging_service.py`, uncomment the Twilio block and add:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxx
TWILIO_FROM_NUMBER=+15555555555
```

### Add more lead sources
Extend `services/lead_finder.py` with:
- Yelp Fusion API
- Yellow Pages scraper
- LinkedIn (for B2B)

### Add email finding
Add Hunter.io or Apollo.io integration in the lead detail page to automatically find the owner's email.

### Add CSV export
```python
@router.get("/export/csv")
async def export_leads_csv(user, db):
    import csv, io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[...])
    # write leads
    return StreamingResponse(output, media_type="text/csv")
```

### Enable Celery workers
Set `REDIS_URL` in .env, then the worker service in docker-compose handles background scraping and sequence scheduling automatically.

---

## Revenue Model

Run this as a SaaS with Stripe subscriptions:

- **Free tier**: 25 credits/month — enough to find, audit, and pitch ~5 leads
- **Pro ($49/month)**: 500 credits/month — enough for a full active pipeline

Conversion flow:
1. User hits free credit limit after initial exploration
2. Upgrade CTA appears on Dashboard and Credit balance widget
3. Stripe Checkout handles subscription
4. Credits reset monthly; webhook upgrades their account plan

At 50 Pro subscribers = **$2,450/month recurring** for a solo tool.

---

## Security Notes

- All API routes (except /auth/*) require a valid JWT
- Passwords hashed with bcrypt (cost factor 12)
- API keys stored in environment variables, never in code
- Stripe webhook signature verified before processing
- Users can only access their own leads/audits/messages (user_id filter on every query)

---

## License

MIT — use freely for personal and commercial projects.

---

Built with ⚡ by [Goggin Digital](https://goggindigital.com)
