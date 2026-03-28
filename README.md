# Final Year Project

## Overview
This project is a full-stack application consisting of a FastAPI backend and a React Native (Expo) frontend. The backend provides APIs for audio processing, authentication, reporting, and more, while the frontend offers a mobile interface for users to interact with the system.

---

## Project Structure

```
final-year-project/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── schemas/
│   │   └── main.py
│   ├── batch_processor.py
│   ├── seed_data.py
│   ├── test_audio.py
│   ├── test_llm.py
│   └── data/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── constants/
│   ├── hooks/
│   ├── scripts/
│   ├── assets/
│   ├── package.json
│   └── ...
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## Backend

### Main Technologies
- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL (with pgvector)
- Pydantic
- Sentence Transformers
- OpenAI Whisper
- python-jose, passlib, python-multipart, email-validator

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
   - Edit or create a `.env` file in the backend directory with your database URL and any secret keys required by the app.
   - Example:
     ```env
     DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/yourdb
     SECRET_KEY=your_secret_key
     ```
5. **Run database migrations (if any):**
   - (Add Alembic or migration instructions here if used)
6. **Start the backend server:**
   ```sh
   cd backend
   uvicorn app.main:app --reload
   ```
   - The API will be available at `http://127.0.0.1:8000`.
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
   cd ../frontend
   ```
2. **Install dependencies:**
   ```sh
   npm install
   ```
3. **Start the Expo development server:**
   ```sh
   npx expo start
   ```
4. **Run on your device or emulator:**
   - Use the Expo Go app or an emulator to scan the QR code and launch the app.

---

## Docker (Optional)
- A `docker-compose.yml` is provided for containerized deployment.
- Update environment variables in the compose file as needed.
- Start all services:
  ```sh
  docker-compose up --build
  ```

---

## Version Information
- Python: 3.11+
- Node.js: 18+
- npm: 9+
- FastAPI: ^0.110
- SQLAlchemy: ^2.0
- React Native: ^0.73
- Expo: ^50

---

## Development Process
- Backend and frontend are developed independently.
- Use virtual environments for Python and node_modules for JS dependencies.
- All large files and virtual environments are excluded from git tracking.
- Requirements and dependencies are kept up to date in `requirements.txt` and `package.json`.

---

## Common Issues
- If you encounter missing Python modules, run `pip install -r requirements.txt` again.
- For large file errors on git push, ensure `.venv/`, `venv/`, and all large binaries are in `.gitignore`.
- For database errors, check your `DATABASE_URL` and ensure PostgreSQL is running.

---

## Contact
For questions or support, open an issue on the GitHub repository or contact the maintainer.
