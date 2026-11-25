const BASE_URL = "http://localhost:5000";

export const BLOOD = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

export function getToken() {
  return localStorage.getItem("bf_token");
}
export function setToken(t) {
  if (t) localStorage.setItem("bf_token", t);
  else localStorage.removeItem("bf_token");
}

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
    throw new Error("Cannot reach server at " + BASE_URL + url + ". Is the backend running? (python app.py)");
  }

  const text = await res.text().catch(() => "");
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }

  if (!res.ok) {
    if (res.status === 401) setToken(null);
    throw new Error((data && (data.error || data.message)) || ("Server error " + res.status));
  }
  return data;
}