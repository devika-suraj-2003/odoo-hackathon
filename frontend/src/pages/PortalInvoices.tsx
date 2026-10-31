import { Fragment, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { FileText, Download, CreditCard, LoaderCircle, Clock, TriangleAlert, ReceiptText } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import { useAuth } from "../context/AuthContext";
import StatusBadge from "../components/StatusBadge";
import { formatINR } from "../lib/money";

type Invoice = { id: number; number: string; status: string; invoice_date?: string | null; due_date?: string | null; total: number; amount_due?: number };

const todayStr = () => new Date().toISOString().slice(0, 10);
const fmt = (d?: string | null) => (d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—");

function loadRazorpay(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(Boolean(window.Razorpay));
    s.onerror = () => {
      s.remove();
      resolve(false);
    };
    document.body.appendChild(s);
  });
}

export default function PortalInvoices() {
  const { user } = useAuth();
  const [items, setItems] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [historyInvoice, setHistoryInvoice] = useState<number | null>(null);
  const [paymentHistory, setPaymentHistory] = useState<Record<number, Payment[]>>({});
  const [historyLoading, setHistoryLoading] = useState<number | null>(null);

  async function load() {
    try {
      const { data } = await api.get("/invoices/");
      const all: Invoice[] = Array.isArray(data) ? data : [];
      setItems(all.filter((i) => i.status !== "draft" && (!i.customer || i.customer.id === user?.id)));
    } catch (err) {
      toast.error(errorMessage(err, "Could not load your invoices"), { id: "portal-inv" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const unpaid = items.filter((i) => i.status === "confirmed" && (i.amount_due ?? i.total) > 0);
  const overdue = unpaid.filter((i) => !!i.due_date && i.due_date < todayStr());
  const totalDue = unpaid.reduce((s, i) => s + (i.amount_due ?? i.total), 0);

  async function downloadPdf(inv: Invoice) {
    setBusy(inv.id);
    try {
      const res = await api.get(`/invoices/${inv.id}/pdf`, { responseType: "blob" });
      window.open(URL.createObjectURL(new Blob([res.data], { type: "application/pdf" })), "_blank");
    } catch {
      toast.error("PDF not available yet");
    } finally {
      setBusy(null);
    }
  }

  async function togglePaymentHistory(inv: Invoice) {
    if (historyInvoice === inv.id) {
      setHistoryInvoice(null);
      return;
    }
    if (paymentHistory[inv.id]) {
      setHistoryInvoice(inv.id);
      return;
    }
    setHistoryLoading(inv.id);
    try {
      const { data } = await api.get("/payments", { params: { invoice_id: inv.id } });
      setPaymentHistory((history) => ({
        ...history,
        [inv.id]: Array.isArray(data) ? data : [],
      }));
      setHistoryInvoice(inv.id);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load payment history"));
    } finally {
      setHistoryLoading(null);
    }
  }

  async function payNow(inv: Invoice) {
    setBusy(inv.id);
    try {
      if (!(await loadRazorpay())) {
        throw new Error("Could not load Razorpay Checkout. Check your internet connection and try again.");
      }
      const { data } = await api.post("/payments/razorpay/order", { invoice_id: inv.id });
      if (!window.Razorpay) throw new Error("Razorpay Checkout did not load. Check your connection and try again.");
      const rzp = new window.Razorpay({
        key: data.key_id,
        amount: data.amount,
        currency: data.currency ?? "INR",
        order_id: data.order_id,
        name: "Brightloop Software",
        description: `Invoice ${inv.number}`,
        prefill: { name: user?.name, email: user?.email },
        theme: { color: "#4f46e5" },
        handler: async (resp: RazorpayPaymentResponse) => {
          try {
            await api.post("/payments/razorpay/verify", {
              invoice_id: inv.id,
              razorpay_order_id: resp.razorpay_order_id,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature: resp.razorpay_signature,
            });
            toast.success("Payment successful. Thank you!");
            load();
          } catch (err) {
            toast.error(errorMessage(err, "Payment could not be verified"));
          } finally {
            setBusy(null);
          }
        },
        modal: { ondismiss: () => setBusy(null) },
      });
      rzp.on("payment.failed", (response) => {
        toast.error(response.error?.description ?? "Payment was not completed.");
        setBusy(null);
      });
      rzp.open();
    } catch (err) {
      toast.error(errorMessage(err, "Online payment is not available"));
      setBusy(null);
    } finally {
      if (!window.Razorpay) setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl bg-linear-to-br from-indigo-600 to-violet-600 p-5 text-white shadow-sm">
          <p className="text-sm text-indigo-100">Total due</p>
          <p className="mt-2 text-3xl font-extrabold">{formatINR(totalDue)}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="flex items-center gap-2 text-sm text-slate-500">
            <Clock className="h-4 w-4 text-amber-500" /> Unpaid invoices
          </p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{unpaid.length}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="flex items-center gap-2 text-sm text-slate-500">
            <TriangleAlert className="h-4 w-4 text-red-500" /> Overdue
          </p>
          <p className="mt-2 text-3xl font-bold text-red-600">{overdue.length}</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3">Invoice</th>
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Due</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3 text-right">Paid</th>
              <th className="px-5 py-3 text-right">Amount due</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-16 text-center">
                  <FileText className="mx-auto h-10 w-10 text-slate-300" />
                  <p className="mt-3 font-semibold text-slate-700">No invoices yet</p>
                </td>
              </tr>
            )}
            {items.map((inv) => {
              const due = inv.amount_due ?? inv.total;
              const isOver = inv.status === "confirmed" && !!inv.due_date && inv.due_date < todayStr() && due > 0;
              const canPay = inv.status === "confirmed" && due > 0;
              return (
                <Fragment key={inv.id}>
                  <tr key={inv.id}>
                    <td className="px-5 py-4 font-semibold text-slate-900">{inv.number}</td>
                    <td className="px-5 py-4 text-slate-600">{fmt(inv.invoice_date)}</td>
                    <td className={`px-5 py-4 ${isOver ? "font-semibold text-red-600" : "text-slate-600"}`}>{fmt(inv.due_date)}</td>
                    <td className="px-5 py-4">
                      <StatusBadge status={isOver ? "overdue" : inv.status} />
                    </td>
                    <td className="px-5 py-4 text-right text-emerald-700">{formatINR(inv.amount_paid ?? 0)}</td>
                    <td className="px-5 py-4 text-right font-semibold text-slate-900">{formatINR(due)}</td>
                    <td className="px-5 py-4">
                      <div className="flex justify-end gap-2">
                        <button onClick={() => downloadPdf(inv)} disabled={busy !== null} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-indigo-600" title="Download PDF">
                          <Download className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => togglePaymentHistory(inv)}
                          disabled={historyLoading !== null}
                          className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-indigo-600 disabled:opacity-60"
                          title="Payment history"
                        >
                          {historyLoading === inv.id ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ReceiptText className="h-4 w-4" />}
                        </button>
                        {canPay && (
                          <button
                            onClick={() => payNow(inv)}
                            disabled={busy !== null}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
                          >
                            {busy === inv.id ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <CreditCard className="h-3.5 w-3.5" />}
                            Pay now
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {historyInvoice === inv.id && (
                    <tr key={`${inv.id}-history`}>
                      <td colSpan={7} className="bg-slate-50 px-5 py-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Payment history</p>
                        {paymentHistory[inv.id]?.length ? (
                          <div className="mt-2 divide-y divide-slate-200">
                            {paymentHistory[inv.id].map((payment) => (
                              <div key={payment.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                                <span className="text-slate-600">
                                  {fmt(payment.payment_date)} · {payment.method.replace(/_/g, " ")}
                                  {payment.note ? ` · ${payment.note}` : ""}
                                </span>
                                <span className="font-semibold text-emerald-700">{formatINR(payment.amount)}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-2 text-sm text-slate-500">No payments recorded for this invoice.</p>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}