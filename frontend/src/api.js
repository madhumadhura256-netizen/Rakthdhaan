const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

/* ---------- Dropdown lists (same as the register page) ---------- */

export const BLOOD = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

export const DISEASES = [
  "None", "Diabetes", "Hypertension", "Asthma", "Heart disease",
  "Hepatitis B", "Hepatitis C", "HIV", "Malaria", "Tuberculosis",
  "Anemia", "Thyroid", "Kidney disease", "Liver disease", "Cancer",
];

export const BAD_HABITS = [
  "None", "Smoking", "Alcohol", "Drug use", "Tobacco", "Betel nut",
  "Smoking and alcohol", "Alcohol and tobacco",
];

export const DISORDERS = [
  "None", "Bleeding disorder", "Clotting disorder", "Seizure disorder",
  "Autoimmune disease", "Allergies", "Blood disorder", "Lymphatic disorder",
];

/* ---------- Auth helpers (role is read from the JWT) ---------- */

export const STAFF_ROLES = ["admin", "doctor", "paramedical", "blood_connect"];

export function getToken() {
  return localStorage.getItem("bf_token");
}

export function setToken(t) {
  if (t) localStorage.setItem("bf_token", t);
  else localStorage.removeItem("bf_token");
}

// Save or clear the token and tell the navbar to refresh
export function setAuth(token) {
  setToken(token);
  window.dispatchEvent(new Event("auth-change"));
}

export function currentUser() {
  const t = getToken();
  if (!t) return null;
  try {
    const b64 = t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const p = JSON.parse(atob(b64));
    if (p.exp && p.exp * 1000 < Date.now()) return null;
    return p;
  } catch {
    return null;
  }
}

export function hasStaffAccess(user) {
  return !!user && STAFF_ROLES.includes(user.role);
}

/* ---------- Form / data helpers ---------- */

export function formToObject(form) {
  const fd = new FormData(form);
  const o = {};
  for (const [k, v] of fd.entries()) o[k] = v;
  return o;
}

export function asList(d, key) {
  if (Array.isArray(d)) return d;
  if (d && Array.isArray(d[key])) return d[key];
  return [];
}

/* ---------- API call ---------- */

export async function api(path, method = "GET", body) {
  const url = typeof path === "function" ? path() : path;

  const opts = {
    method: String(method).toUpperCase(),
    headers: {},
  };

  if (body && Object.keys(body).length) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }

  const token = getToken();
  if (token) opts.headers.Authorization = "Bearer " + token;

  let res;
  try {
    res = await fetch(BASE_URL + url, opts);
  } catch (e) {
    throw new Error(
      "Cannot reach server at " + BASE_URL + url + ". Is the backend running? (python app.py)"
    );
  }

  const text = await res.text().catch(() => "");
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }

  if (!res.ok) {
    if (res.status === 401) setToken(null);
    throw new Error(
      (data && (data.error || data.message)) || "Server error " + res.status
    );
  }

  return data;
}