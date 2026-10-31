import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import toast, { Toaster } from "react-hot-toast";
import { AuthProvider } from "./context/AuthContext";
import App from "./App";
import { applyPalette, getPalette } from "./lib/theme";
import { fireConfetti } from "./lib/confetti";
import "./index.css";

try {
  if (localStorage.getItem("theme") === "dark") document.documentElement.classList.add("dark");
} catch {}
applyPalette(getPalette());

// Celebrate every successful payment with confetti (admin "Payment recorded" and customer "Payment successful").
const originalSuccess = toast.success;
toast.success = ((message: any, options?: any) => {
  if (typeof message === "string" && /payment/i.test(message)) fireConfetti();
  return originalSuccess(message, options);
}) as typeof toast.success;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              borderRadius: "14px",
              fontSize: "14px",
              fontWeight: 600,
              padding: "12px 16px",
              boxShadow: "0 18px 40px -18px rgba(15, 23, 42, 0.45)",
            },
          }}
        />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
