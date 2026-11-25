import { createContext, useContext, useState, useEffect } from "react";
import { api, getToken, setToken } from "../api";

const AuthContext = createContext(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (token) {
      api("/api/donors/me")
        .then((d) => setUser({ role: "donor", ...d }))
        .catch(() => setToken(null))
        .finally(() => setReady(true));
    } else {
      setReady(true);
    }
  }, []);

  const login = async (email, password) => {
    const res = await api("/api/auth/login", "POST", { email, password });
    setToken(res.token);
    setUser(res.user);
    return res;
  };

  const register = async (data) => {
    const res = await api("/api/auth/register", "POST", data);
    setToken(res.token);
    setUser(res.user);
    return res;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  if (!ready) {
    return (
      <div className="app-loading">
        <div className="spinner" /> Loading...
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}