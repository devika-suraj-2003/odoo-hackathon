import { useEffect, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";

export default function Modal({
  open,
  title,
  onClose,
  children,
  wide,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="modal"
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/40 p-4 backdrop-blur-md sm:items-center"
          onMouseDown={onClose}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <motion.div
            className={`bl-modal my-8 w-full ${wide ? "max-w-2xl" : "max-w-lg"} overflow-hidden rounded-3xl border border-white/60 bg-white shadow-[0_30px_80px_-20px_rgba(49,46,129,0.45)]`}
            onMouseDown={(e) => e.stopPropagation()}
            initial={{ opacity: 0, y: 18, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
          >
            <div className="relative flex items-center justify-between border-b border-slate-200/70 px-6 py-4">
              <div className="bl-bar pointer-events-none absolute inset-x-0 top-0 h-1" />
              <h3 className="text-lg font-bold text-slate-900">{title}</h3>
              <button onClick={onClose} className="rounded-xl p-1.5 text-slate-400 transition hover:rotate-90 hover:bg-slate-100 hover:text-slate-700">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="px-6 py-5">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
