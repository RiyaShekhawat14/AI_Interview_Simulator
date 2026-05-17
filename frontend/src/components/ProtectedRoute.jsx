import { Navigate, useLocation } from "react-router-dom";

import { isAuthenticated } from "../services/api";

function ProtectedRoute({ children }) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/auth" replace state={{ redirectTo: location.pathname }} />;
  }

  return children;
}

export default ProtectedRoute;
