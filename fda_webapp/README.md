# NutriChat — Food Nutrition AI

Upload a food photo and get an instant FDA-style Nutrition Facts label, then chat back and forth with the AI about what you're eating.

**Stack:** FastAPI · React (Vite + TSX) · Tailwind CSS · Groq

---

## Quick Start

### 1. Get a Groq API key
Sign up at [console.groq.com](https://console.groq.com) (free tier available).

### 2. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # then add your GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install   # already done if you cloned fresh
npm run dev   # http://localhost:5173
```

Or double-click `start.bat` to launch both in separate terminals.

---

## How it works

| Step | What happens |
|---|---|
| Upload photo | Image is sent to FastAPI → Groq vision model (`llama-4-scout`) → FDA-style Nutrition Facts label |
| Chat | Your messages + full conversation history → Groq chat model (`llama-3.3-70b`) → contextual dietary advice |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/analyze-food` | Upload image → Nutrition Facts label |
| `POST` | `/api/chat` | Chat messages → AI reply |
| `GET` | `/api/health` | Health check |
