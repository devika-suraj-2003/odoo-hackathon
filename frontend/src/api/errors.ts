export function errorMessage(err: any, fallback = "Something went wrong") {
  if (err?.response) {
    const detail = err.response.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    return fallback;
  }
  if (err?.request) return "Cannot reach the server. Is the backend running?";
  return err?.message || fallback;
}