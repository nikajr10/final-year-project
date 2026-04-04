# SmartBiz AI — Final Year Project

## Overview
SmartBiz AI is a full-stack intelligent inventory management system for Nepali retail shops. It combines **voice-powered inventory control** (Nepali speech → stock updates) with an **AI-powered business assistant chatbot** — all running locally with no cloud dependency.

### Key Features
- 🎙️ **Voice Inventory Management** — Speak commands in Nepali to add, remove, or check stock
- 🤖 **AI Business Chatbot** — Ask questions about stock, sales, and business health in natural language
- 📊 **Sales Reports** — Generate and download PDF sales reports
- 📦 **Real-time Inventory Dashboard** — View all products with low-stock alerts
- 🔐 **User Authentication** — Secure login/signup system

---

## Project Structure

```
final-year-project/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py          # Login/register endpoints
│   │   │   ├── chatbot.py       # AI chatbot API (5 quick actions + free text)
│   │   │   ├── reports.py       # PDF sales report generation
│   │   │   └── routes.py        # Voice transaction endpoints
│   │   ├── core/
│   │   │   ├── ai_service.py    # Qwen 2.5 7B chatbot brain (via Ollama)
│   │   │   ├── config.py        # App settings (DATABASE_URL, etc.)
│   │   │   ├── llm_service.py   # Llama3 intent parser for voice commands
│   │   │   ├── security.py      # JWT token utilities
│   │   │   ├── vector_matcher.py # SBERT + pgvector product matching
│   │   │   └── whisper_service.py # OpenAI Whisper speech-to-text
│   │   ├── db/
│   │   │   ├── crud.py          # Database CRUD operations
│   │   │   ├── models.py        # SQLAlchemy models (Product, User, etc.)
│   │   │   └── session.py       # Database session management
│   │   ├── schemas/
│   │   │   ├── auth.py          # Auth request/response schemas
│   │   │   └── chatbot.py       # Chat request/response schemas
│   │   └── main.py              # FastAPI entry point
│   ├── seed_data.py             # Seed initial product data
│   ├── requirements.txt         # Python dependencies
│   └── .env                     # Environment variables
├── frontend/
│   ├── app/
│   │   ├── (auth)/              # Login & Signup screens
│   │   ├── (tabs)/
│   │   │   ├── index.tsx        # Home dashboard
│   │   │   ├── inventory.tsx    # Inventory list with search
│   │   │   ├── assistant.tsx    # AI chatbot interface
│   │   │   ├── sales.tsx        # Sales reports
│   │   │   └── profile.tsx      # User profile
│   │   └── (screens)/
│   │       └── voice.tsx        # Voice recording screen
│   ├── constants/
│   │   └── Config.ts            # API_URL and timeout settings
│   ├── components/              # Reusable UI components
│   └── package.json             # Node.js dependencies
├── requirements.txt             # Root-level Python dependencies
├── docker-compose.yml           # Docker containerized deployment
└── README.md
```

---

## AI Models Used

| Model | Purpose | Size | Runtime |
|-------|---------|------|---------|
| **Qwen 2.5 7B** | Business chatbot (analyst, stock info, assistant) | ~4.7 GB | Ollama (local) |
| **Llama 3** | Voice command intent parsing (regex fallback) | ~4.7 GB | Ollama (local) |
| **OpenAI Whisper Medium** | Nepali speech-to-text transcription | ~1.5 GB | Local Python |
| **all-MiniLM-L6-v2** | SBERT embeddings for product matching | ~90 MB | Local Python |

> All models run **100% locally** — no internet or API keys required after initial download.

---

## AI Chatbot Features

The SmartBiz AI chatbot serves three roles:

### 📊 Business Analyst
- Analyze sales trends and identify best/worst sellers
- Calculate stock turnover and days-until-stockout
- Provide restocking recommendations with order quantities

### 📦 Stock Information Provider
- Report exact stock levels for any product
- Alert on low stock (critical < 10 units, warning < 40 units)
- Compare stock across products

### 🤖 General Assistant
- Answer general business questions
- Provide pricing and strategy advice
- Support multi-turn conversations with context memory

### Quick Actions
| Button | What It Does |
|--------|-------------|
| **Low Stock** | Lists critically low and warning-level items with restock priority |
| **Today's Sales** | Aggregated daily sales with best-seller identification |
| **Summary** | Full business health overview with weekly transaction stats |
| **Top Products** | Best-selling products by 30-day volume |
| **Restock** | Calculates days-until-stockout using sales velocity, suggests order quantities |

---

## Backend

### Main Technologies
- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL (with pgvector + HNSW index)
- Pydantic v2
- Sentence Transformers (SBERT)
- OpenAI Whisper
- httpx (async HTTP client for Ollama)
- Ollama (local LLM runtime)

### Setup Instructions

1. **Clone the repository:**
   ```sh
   git clone https://github.com/nikajr10/final-year-project.git
   cd final-year-project/backend
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the `backend/` directory:
   ```env
   DATABASE_URL=postgresql://superuser:finalpassword@127.0.0.1:5435/final_inventory
   ```

5. **Start PostgreSQL with pgvector:**
   ```sh
   docker-compose up -d
   ```

6. **Seed the database (first time only):**
   ```sh
   python seed_data.py
   ```

7. **Install and start Ollama:**
   ```sh
   # Install Ollama (https://ollama.ai)
   # Then pull the required models:
   ollama pull qwen2.5:7b
   ollama pull llama3
   ```

8. **Start the backend server:**
   ```sh
   uvicorn app.main:app --reload --host 0.0.0.0
   ```
   - API: `http://127.0.0.1:8000`
   - Interactive docs: `http://127.0.0.1:8000/docs`

---

## Frontend

### Main Technologies
- React Native (Expo)
- TypeScript
- NativeWind (Tailwind CSS for React Native)

### Setup Instructions

1. **Navigate to the frontend directory:**
   ```sh
   cd frontend
   ```

2. **Install dependencies:**
   ```sh
   npm install
   ```

3. **Configure the backend IP:**
   Edit `frontend/constants/Config.ts` and set `BACKEND_IP` to your backend machine's IP address:
   ```ts
   const BACKEND_IP = "192.168.1.92"; // ← Change to your backend IP
   ```

4. **Start the Expo development server:**
   ```sh
   npx expo start
   ```

5. **Run on your device or emulator:**
   Use the Expo Go app or an emulator to scan the QR code.

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login and receive JWT token |

### AI Chatbot
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/chat` | Send a message or quick action to the AI chatbot |

**Request body:**
```json
{
  "message": "How is my stock looking?",
  "action": null,
  "history": [
    {"role": "user", "text": "previous question"},
    {"role": "ai", "text": "previous answer"}
  ]
}
```

### Voice Inventory
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/inventory/voice-transaction` | Process a voice command audio file |
| POST | `/process-voice` | Legacy voice processing endpoint |
| GET | `/stock` | Get all product stock levels |
| POST | `/refresh-embeddings` | Re-encode all product embeddings |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/sales-pdf` | Generate PDF sales report |

---

## Docker (Optional)

A `docker-compose.yml` is provided for containerized deployment:
```sh
docker-compose up --build
```

---

## Version Information

| Component | Version |
|-----------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |
| FastAPI | ^0.135 |
| SQLAlchemy | ^2.0 |
| React Native | ^0.73 |
| Expo | ^50 |
| Ollama | Latest |
| Qwen 2.5 | 7B |

---

## Development Notes

- Backend and frontend are developed independently
- Use virtual environments for Python and `node_modules` for JS dependencies
- All large files (models, venvs) are excluded from Git via `.gitignore`
- The chatbot uses **Qwen 2.5 7B** via Ollama for business analysis
- Voice commands use **Llama 3** for intent parsing and **Whisper Medium** for transcription
- Product matching uses **SBERT embeddings** with **pgvector HNSW index** for O(log n) search

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Missing Python modules | Run `pip install -r requirements.txt` |
| Chatbot not responding | Ensure Ollama is running: `ollama run qwen2.5:7b` |
| Cannot connect to backend | Check `BACKEND_IP` in `frontend/constants/Config.ts` |
| Database errors | Verify `DATABASE_URL` in `.env` and ensure PostgreSQL is running |
| Large file errors on push | Ensure `.venv/`, `node_modules/` are in `.gitignore` |
| Voice commands not working | Ensure Whisper model is downloaded and `ollama run llama3` is running |

---

## Contact
For questions or support, open an issue on the GitHub repository or contact the maintainer.
