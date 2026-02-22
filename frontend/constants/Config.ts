// Use the IP address of the backend laptop here
const BACKEND_IP = "192.168.1.95";

export const API_URL = `http://${BACKEND_IP}:8000`;

export const ENDPOINTS = {
  REGISTER: `${API_URL}/auth/register`,
  LOGIN: `${API_URL}/auth/login`,
  INVENTORY: `${API_URL}/inventory`,
};
