import { Navigate, Outlet } from "react-router-dom";
import { useAuth, homeFor, type Role } from "../context/AuthContext";

export default function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return <Outlet />;
}