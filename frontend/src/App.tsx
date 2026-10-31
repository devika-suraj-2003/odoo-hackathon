import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth, homeFor } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Placeholder from "./pages/Placeholder";

const STAFF_PAGES = [
  ["dashboard", "Dashboard"], ["customers", "Customers"], ["subscriptions", "Subscriptions"],
  ["invoices", "Invoices"], ["payments", "Payments"],
];
const ADMIN_PAGES = [
  ["products", "Products"], ["plans", "Plans"], ["templates", "Quotation Templates"],
  ["taxes", "Taxes"], ["discounts", "Discounts"], ["staff", "Staff"],
];
const CUSTOMER_PAGES = [
  ["portal/subscriptions", "My Subscriptions"], ["portal/invoices", "My Invoices"],
  ["portal/profile", "Profile"],
];

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route element={<ProtectedRoute roles={["admin", "staff"]} />}>
            {STAFF_PAGES.map(([path, title]) => (
              <Route key={path} path={path} element={<Placeholder title={title} />} />
            ))}
          </Route>
          <Route element={<ProtectedRoute roles={["admin"]} />}>
            {ADMIN_PAGES.map(([path, title]) => (
              <Route key={path} path={path} element={<Placeholder title={title} />} />
            ))}
          </Route>
          <Route element={<ProtectedRoute roles={["customer"]} />}>
            {CUSTOMER_PAGES.map(([path, title]) => (
              <Route key={path} path={path} element={<Placeholder title={title} />} />
            ))}
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Home />} />
    </Routes>
  );
}