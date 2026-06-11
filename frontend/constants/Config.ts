// Use the IP address of the backend laptop here
const BACKEND_IP = "172.20.10.2";

// ─── API Base URL ────────────────────────────────────────────────────────────
// All screens import this to hit the FastAPI backend.
export const API_URL = `http://${BACKEND_IP}:8000`;

export const FETCH_TIMEOUT_MS = 80000;       // 80 s – regular API calls
export const VOICE_TIMEOUT_MS = 270000;      // 4.5 min – voice upload + Whisper medium transcription
export const CHAT_TIMEOUT_MS = 120000;      // 2 min  – LLM chatbot can be slower
export const LOW_STOCK_THRESHOLD = 40;
