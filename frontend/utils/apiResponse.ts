export async function readApiResponse(response: Response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return {
    detail: text.trim() || `Server returned ${response.status}.`,
  };
}

export function getApiErrorMessage(
  payload: any,
  fallback = "Something went wrong. Please try again.",
) {
  const detail = payload?.detail ?? payload?.message ?? payload?.error;

  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || String(item)).join("\n");
  }

  if (typeof detail === "string" && detail.trim()) {
    if (detail.trim().toLowerCase() === "internal server error") {
      return "The server had a problem processing this request. Please try again.";
    }
    return detail;
  }

  return fallback;
}
