import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth, homeFor } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Products from "./pages/Products";
import Plans from "./pages/Plans";
import Subscriptions from "./pages/Subscriptions";
import SubscriptionDetail from "./pages/SubscriptionDetail";
import Invoices from "./pages/Invoices";
import InvoiceDetail from "./pages/InvoiceDetail";
import Payments from "./pages/Payments";
import PortalSubscriptions from "./pages/PortalSubscriptions";
import PortalInvoices from "./pages/PortalInvoices";
import PortalProfile from "./pages/PortalProfile";
import Dashboard from "./pages/Dashboard";
import People from "./pages/People";
import Taxes from "./pages/Taxes";
import Discounts from "./pages/Discounts";
import Templates from "./pages/Templates";

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/reset" element={<ResetPassword />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route element={<ProtectedRoute roles={["admin", "staff"]} />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/customers" element={<People role="customer" />} />
            <Route path="/subscriptions" element={<Subscriptions />} />
            <Route path="/subscriptions/:id" element={<SubscriptionDetail />} />
            <Route path="/invoices" element={<Invoices />} />
            <Route path="/invoices/:id" element={<InvoiceDetail />} />
            <Route path="/payments" element={<Payments />} />
          </Route>

          <Route element={<ProtectedRoute roles={["admin"]} />}>
            <Route path="/products" element={<Products />} />
            <Route path="/plans" element={<Plans />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/taxes" element={<Taxes />} />
            <Route path="/discounts" element={<Discounts />} />
            <Route path="/staff" element={<People role="staff" />} />
          </Route>

          <Route element={<ProtectedRoute roles={["customer"]} />}>
            <Route path="/portal/subscriptions" element={<PortalSubscriptions />} />
            <Route path="/portal/invoices" element={<PortalInvoices />} />
            <Route path="/portal/profile" element={<PortalProfile />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Home />} />
    </Routes>
  );
}