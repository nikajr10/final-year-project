// Replace 192.168.1.XX with the ACTUAL IP of the backend laptop
// You find this by typing 'ipconfig' on the backend laptop.
export const BASE_URL = "http://192.168.1.95:8000";

export const API_ROUTES = {
  REGISTER: `${BASE_URL}/auth/register`,
  LOGIN: `${BASE_URL}/auth/login`,
  INVENTORY: `${BASE_URL}/inventory`,
};
