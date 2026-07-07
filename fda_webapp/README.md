# NutriChat — Food Nutrition AI

A fullstack web app that analyzes food photos and provides FDA-style Nutrition Facts labels via AI-powered chat. Built with **FastAPI** (backend) + **Next.js** (frontend) using **Groq** as the AI provider.

## Features

- 📸 Upload a food photo (drag & drop, click, or take a photo on mobile)
- 🏷️ Instant FDA-style Nutrition Facts label with macros, micros & % Daily Values
- 💬 Back-and-forth conversation about the food (calories, healthier alternatives, diet fit, etc.)
- ⚡ Powered by Groq — blazing fast LLM inference
- 🔄 Upload new photos mid-conversation

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+ |
| AI/Vision | Groq — `llama-4-scout` (vision) + `llama-3.3-70b` (chat) |

---

## Setup

### 1. Get a Groq API Key

Sign up at [console.groq.com](https://console.groq.com) and create an API key (free tier available).

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

copy .env.example .env         # Windows
# cp .env.example .env         # Mac/Linux
# Then edit .env and add your GROQ_API_KEY
```

Start the backend:
```bash
uvicorn main:app --reload --port 8000
```

The API will be available at http://localhost:8000

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:3000

---

## Usage

1. Open http://localhost:3000
2. Drag & drop a food photo or click to browse
3. The AI generates a Nutrition Facts label in seconds
4. Ask follow-up questions — calories, macros, dietary fit, alternatives, etc.
5. Click "New photo" anytime to analyze a different food

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/analyze-food` | Upload image → returns Nutrition Facts label |
| `POST` | `/api/chat` | Send chat messages → returns AI reply |
| `GET` | `/api/health` | Health check |
