import { useEffect, useState } from "react";
import { api, asList, formToObject, BLOOD, getToken, setToken } from "./api";

/* ---------- auth helpers (read the role straight from the JWT) ---------- */
const STAFF_ROLES = ["admin", "doctor", "paramedical", "blood_connect"];

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

function hasStaffAccess(user) {
  return !!user && STAFF_ROLES.includes(user.role);
}

// Save or clear the login token and tell the navbar to refresh
export function setAuth(token) {
  setToken(token);
  window.dispatchEvent(new Event("auth-change"));
}

/* ---------- small helpers ---------- */
const Msg = ({ m }) =>
  m ? <div className={"msg " + (m.ok ? "ok" : "err")}>{m.text}</div> : null;

const BloodSelect = ({ any }) => (
  <select name="blood_group" required={!any}>
    {any && <option value="">Any</option>}
    {BLOOD.map((b) => <option key={b}>{b}</option>)}
  </select>
);

function Table({ rows, cols }) {
  if (!rows.length) return <div className="empty">Nothing to show yet.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{cols.map((c) => <th key={c[0]}>{c[0]}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id ?? i}>
              {cols.map((c) => <td key={c[1]}>{String(r[c[1]] ?? "")}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ApiForm({ path, method = "POST", extra = {}, okText, children, button }) {
  const [msg, setMsg] = useState(null);
   async function submit(e) {
    e.preventDefault();
    const form = e.target;
    const body = { ...formToObject(form), ...extra };

    // Number boxes give text ("5"); the server wants real numbers (5)
    Array.from(form.elements).forEach((el) => {
      if (el.name && el.type === "number" && el.value !== "") {
        body[el.name] = Number(el.value);
      }
    });

    try {
      const d = await api(path(form), method, body);
      setMsg({ ok: true, text: (d && d.message) || okText });
      form.reset();
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }
  return (
    <div className="card">
      <form onSubmit={submit}>{children}
        <div className="full"><button>{button}</button></div>
      </form>
      <Msg m={msg} />
    </div>
  );
}

function LocationFields() {
  function fill(e) {
    const form = e.target.form;
    navigator.geolocation?.getCurrentPosition(
      (p) => {
        form.latitude.value = p.coords.latitude.toFixed(5);
        form.longitude.value = p.coords.longitude.toFixed(5);
      },
      () => alert("Could not read your location. Enter latitude and longitude by hand.")
    );
  }
  return (
    <>
      <label>City<input name="city" required /></label>
      <label>Latitude<input name="latitude" type="number" step="any" required /></label>
      <label>Longitude<input name="longitude" type="number" step="any" required /></label>
      <div className="full">
        <button type="button" className="ghost" onClick={fill}>Use my current location</button>
      </div>
    </>
  );
}

/* ---------- Home ---------- */
function CountUp({ to }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (typeof to !== "number") return;
    let raf, start;
    const step = (t) => {
      if (start === undefined) start = t;
      const p = Math.min((t - start) / 900, 1);
      setN(Math.round(to * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [to]);
  if (to === null || to === undefined) return <>…</>;
  return <>{typeof to === "number" ? n : to}</>;
}

export function Home({ go }) {
  const [s, setS] = useState({ donors: null, requests: null, banks: null });
  const [locked, setLocked] = useState(false);
  const [err, setErr] = useState([]);
  const to = (k) => () => go && go(k);

  useEffect(() => {
    const fail = (n) => (e) => {
      setS((p) => ({ ...p, [n]: "–" }));
      if (getToken()) setErr((p) => [...p, `${n}: ${e.message}`]);
      else setLocked(true);
    };
    api("/api/donors")
      .then((d) => setS((p) => ({ ...p, donors: asList(d, "donors").length })))
      .catch(fail("donors"));
    api("/api/requests")
      .then((d) =>
        setS((p) => ({
          ...p,
          requests: asList(d, "requests").filter((r) => !r.status || r.status === "pending").length,
        }))
      )
      .catch(fail("requests"));
    api("/api/bloodbank/banks")
      .then((d) => setS((p) => ({ ...p, banks: asList(d, "banks").length })))
      .catch(fail("banks"));
  }, []);

  return (
    <>
      <section className="hero">
        <h1>One donation.<br />Up to three lives.</h1>
        <svg className="ecg" viewBox="0 0 1200 130" role="img" aria-label="A heartbeat line ending in a blood drop">
          <path className="ecg-line" pathLength="1"
            d="M0 75H300L322 75L346 22L378 118L404 75H640L662 75L686 22L718 118L744 75H1120" />
          <path className="ecg-dot" d="M1146 52c0 0-16 20-16 31a16 16 0 0 0 32 0c0-11-16-31-16-31z" />
        </svg>
        <div className="hero-body">
          <p className="lead">
            Raktdhan connects blood donors, patients' families and blood banks, so the right blood group reaches the right hospital faster.
          </p>
          <div className="hero-cta">
            <button onClick={to("donate")}>Become a donor</button>
            <button className="ghost" onClick={to("request")}>Request blood</button>
          </div>
        </div>
      </section>

      <section className="stats" aria-label="Current numbers">
        <div className="stat"><b><CountUp to={s.donors} /></b><span>Active donors</span></div>
        <div className="stat"><b><CountUp to={s.requests} /></b><span>Pending requests</span></div>
        <div className="stat"><b><CountUp to={s.banks} /></b><span>Blood banks</span></div>
      </section>
      {locked && (
        <p className="note">
          Pending requests and blood banks show after you{" "}
          <button className="link" onClick={to("login")}>log in</button>.
        </p>
      )}
      {err.length > 0 && (
        <Msg m={{ ok: false, text: "Some counts could not load (" + err.join("; ") + "). Is the backend running?" }} />
      )}

      <h2 className="section-title">How it works</h2>
      <ol className="steps">
        <li className="step">
          <span className="step-n">1</span>
          <h3>Register</h3>
          <p>Add your blood group, city and phone number. It takes about two minutes.</p>
        </li>
        <li className="step">
          <span className="step-n">2</span>
          <h3>Get an alert</h3>
          <p>When a verified request near you needs your blood group, you hear about it first.</p>
        </li>
        <li className="step">
          <span className="step-n">3</span>
          <h3>Donate</h3>
          <p>Visit the blood bank and donate. You then rest for 3 months (men) or 4 months (women) before the next one.</p>
        </li>
      </ol>

      <section className="cta-band">
        <h2>Your blood group may be the one a family is searching for today.</h2>
        <button className="plasma" onClick={to("donate")}>Register as a donor</button>
      </section>
    </>
  );
}

/* ---------- Donor registration ---------- */
const DISEASES = [
  "None", "Diabetes", "Hypertension", "Asthma", "Heart disease",
  "Hepatitis B", "Hepatitis C", "HIV", "Malaria", "Tuberculosis",
  "Anemia", "Thyroid", "Kidney disease", "Liver disease", "Cancer"
];
const BAD_HABITS = [
  "None", "Smoking", "Alcohol", "Drug use", "Tobacco", "Betel nut",
  "Smoking and alcohol", "Alcohol and tobacco"
];
const DISORDERS = [
  "None", "Bleeding disorder", "Clotting disorder", "Seizure disorder",
  "Autoimmune disease", "Allergies", "Blood disorder", "Lymphatic disorder"
];

/* ----- helpers for the register page ----- */
const digitsOnly = (v, max) => v.replace(/\D/g, "").slice(0, max);

const todayStr = () => new Date().toISOString().split("T")[0];

// Men can donate again after 3 months, women after 4 months
function cooldownMonths(gender) {
  return gender === "Female" ? 4 : 3;
}

function nextEligibleDate(lastDonation, gender) {
  if (!lastDonation) return null;
  const d = new Date(lastDonation);
  d.setMonth(d.getMonth() + cooldownMonths(gender));
  return d;
}

function isInCooldown(lastDonation, gender) {
  const next = nextEligibleDate(lastDonation, gender);
  return !!next && next > new Date();
}

function formatDate(d) {
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function Field({ label, error, children }) {
  return (
    <div>
      <label>{label}</label>
      {children}
      {error && <small className="field-error">{error}</small>}
    </div>
  );
}

function PasswordInput({ value, onChange, placeholder }) {
  const [show, setShow] = useState(false);
  return (
    <div className="pw-wrap">
      <input
        type={show ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete="new-password"
      />
      <button
        type="button"
        className="pw-toggle"
        onClick={() => setShow(!show)}
        aria-label={show ? "Hide password" : "Show password"}
      >
        {show ? "Hide" : "Show"}
      </button>
    </div>
  );
}

export function DonorRegister({ go }) {
  const [form, setForm] = useState({
    name: "", email: "", password: "", confirm: "",
    phone: "", aadhaar: "",
    blood_group: "O+", gender: "Male", age: "", weight: "",
    previous_hb: "", diseases: "None", bad_habits: "None", disorders: "None",
    sms_consent: false, city: "", latitude: "", longitude: "",
    donated_before: "no", last_donation_date: "",
  });
  const [errors, setErrors] = useState({});
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  // OTP state
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpToken, setOtpToken] = useState("");   // proof from the server that the phone is verified
  const [otpMsg, setOtpMsg] = useState(null);
  const [otpBusy, setOtpBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);    // resend timer in seconds
  const [attempts, setAttempts] = useState(0);

  const verified = !!otpToken;

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  // Resend countdown
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  // If the phone number changes, the old OTP no longer counts
  function changePhone(value) {
    update("phone", digitsOnly(value, 10));
    setOtpSent(false);
    setOtp("");
    setOtpToken("");
    setOtpMsg(null);
    setAttempts(0);
  }

  const phoneValid = /^[6-9]\d{9}$/.test(form.phone);

  async function sendOtp() {
    if (!phoneValid) {
      setErrors((e) => ({ ...e, phone: "Enter a valid 10-digit mobile number starting with 6-9." }));
      return;
    }
    setOtpBusy(true);
    setOtpMsg(null);
    try {
      await api("/api/auth/send-otp", "POST", { phone: form.phone });
      setOtpSent(true);
      setOtp("");
      setAttempts(0);
      setCooldown(30);
      setOtpMsg({ ok: true, text: "OTP sent to +91 " + form.phone });
      setErrors((e) => ({ ...e, phone: "" }));
    } catch (err) {
      setOtpMsg({ ok: false, text: err.message });
    } finally {
      setOtpBusy(false);
    }
  }

  async function verifyOtp() {
    if (otp.length !== 6) {
      setOtpMsg({ ok: false, text: "Enter the 6-digit OTP." });
      return;
    }
    if (attempts >= 5) {
      setOtpMsg({ ok: false, text: "Too many wrong attempts. Please request a new OTP." });
      return;
    }
    setOtpBusy(true);
    try {
      const d = await api("/api/auth/verify-otp", "POST", { phone: form.phone, otp });
      setOtpToken(d.otp_token || "verified");
      setOtpMsg({ ok: true, text: "Phone number verified." });
    } catch (err) {
      setAttempts((a) => a + 1);
      setOtpMsg({ ok: false, text: err.message || "Wrong OTP." });
    } finally {
      setOtpBusy(false);
    }
  }

  function validate() {
    const e = {};

    if (form.name.trim().length < 2) e.name = "Enter your full name.";
    else if (!/^[A-Za-z .'-]+$/.test(form.name.trim())) e.name = "Name can only contain letters.";

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.email.trim())) e.email = "Enter a valid email address.";

    if (form.password.length < 8) e.password = "Password must be at least 8 characters.";
    else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password))
      e.password = "Password must contain at least one letter and one number.";

    if (form.confirm !== form.password) e.confirm = "Passwords do not match.";

    if (!phoneValid) e.phone = "Enter a valid 10-digit mobile number starting with 6-9.";
    else if (!verified) e.phone = "Please verify your phone number with the OTP.";

    if (form.aadhaar && !/^[2-9]\d{11}$/.test(form.aadhaar))
      e.aadhaar = "Aadhaar must be exactly 12 digits and cannot start with 0 or 1.";

    const age = Number(form.age);
    if (!form.age) e.age = "Age is required.";
    else if (age < 18 || age > 65) e.age = "Donors must be between 18 and 65 years old.";

    if (form.weight && Number(form.weight) < 45) e.weight = "Donors must weigh at least 45 kg.";

    if (form.previous_hb && (Number(form.previous_hb) < 5 || Number(form.previous_hb) > 20))
      e.previous_hb = "Enter a realistic haemoglobin value (5-20 g/dL).";

    if (!form.city.trim()) e.city = "City is required.";

    if (form.latitude && (Number(form.latitude) < -90 || Number(form.latitude) > 90))
      e.latitude = "Latitude must be between -90 and 90.";
    if (form.longitude && (Number(form.longitude) < -180 || Number(form.longitude) > 180))
      e.longitude = "Longitude must be between -180 and 180.";

    if (form.donated_before === "yes") {
      if (!form.last_donation_date) e.last_donation_date = "Please enter your last donation date.";
      else if (form.last_donation_date > todayStr()) e.last_donation_date = "Date cannot be in the future.";
    }

    if (!form.sms_consent) e.sms_consent = "SMS consent is needed so we can alert you about requests.";

    setErrors(e);
    return Object.keys(e).length === 0;
  }

  const submit = async (ev) => {
    ev.preventDefault();
    setMsg("");
    if (!validate()) {
      setMsg("Please fix the highlighted fields.");
      return;
    }

    const donatedBefore = form.donated_before === "yes";
    const lastDate = donatedBefore ? form.last_donation_date : "";
    const inactive = donatedBefore && isInCooldown(lastDate, form.gender);
    const nextDate = donatedBefore ? nextEligibleDate(lastDate, form.gender) : null;

    setLoading(true);
    try {
      const { confirm, donated_before, ...rest } = form;   // don't send confirm / radio value
      const d = await api("/api/auth/register", "POST", {
        ...rest,
        role: "donor",
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        age: Number(form.age),
        weight: form.weight ? Number(form.weight) : null,
        previous_hb: form.previous_hb ? Number(form.previous_hb) : null,
        latitude: form.latitude ? Number(form.latitude) : null,
        longitude: form.longitude ? Number(form.longitude) : null,
        sms_consent: form.sms_consent ? 1 : 0,
        has_donated_before: donatedBefore ? 1 : 0,
        last_donation_date: lastDate || null,
        status: inactive ? "inactive" : "active",
        next_eligible_date: nextDate ? nextDate.toISOString().split("T")[0] : null,
        otp_token: otpToken,
      });
      setAuth(d.token || d.access_token);

      setMsg(
        inactive
          ? "Registered successfully! You are inactive until " + formatDate(nextDate) + " and will be alerted once you are eligible again."
          : "Registered successfully! You are now logged in."
      );
      setTimeout(() => go && go("profile"), 1800);
    } catch (err) {
      setMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Live preview of the cooldown for the donor
  const showCooldown = form.donated_before === "yes" && form.last_donation_date && form.last_donation_date <= todayStr();
  const nextDate = showCooldown ? nextEligibleDate(form.last_donation_date, form.gender) : null;
  const stillInactive = showCooldown && isInCooldown(form.last_donation_date, form.gender);

  return (
    <div className="page">
      <h1>Become a Donor</h1>
      <p className="sub">Fields marked * are required.</p>
      {msg && <div className={"msg " + (msg.includes("successfully") ? "success" : "error")}>{msg}</div>}

      <form className="card" onSubmit={submit} noValidate>
        <h2>Personal Details</h2>
        <div className="form-row">
          <Field label="Full Name *" error={errors.name}>
            <input value={form.name} onChange={(e) => update("name", e.target.value)} placeholder="Rahul Sharma" />
          </Field>
          <Field label="Email *" error={errors.email}>
            <input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} placeholder="rahul@example.com" />
          </Field>
        </div>

        <div className="form-row">
          <Field label="Password * (min 8, letters and numbers)" error={errors.password}>
            <PasswordInput value={form.password} onChange={(e) => update("password", e.target.value)} />
          </Field>
          <Field label="Confirm Password *" error={errors.confirm}>
            <PasswordInput value={form.confirm} onChange={(e) => update("confirm", e.target.value)} />
          </Field>
        </div>

        <div className="form-row">
          <Field label="Phone * (10 digits)" error={errors.phone}>
            <div className="otp-row">
              <input
                type="tel"
                inputMode="numeric"
                maxLength={10}
                value={form.phone}
                onChange={(e) => changePhone(e.target.value)}
                placeholder="9876543210"
                disabled={verified}
              />
              {!verified && (
                <button
                  type="button"
                  className="ghost sm"
                  onClick={sendOtp}
                  disabled={otpBusy || cooldown > 0 || !phoneValid}
                >
                  {cooldown > 0 ? "Resend in " + cooldown + "s" : otpSent ? "Resend OTP" : "Send OTP"}
                </button>
              )}
              {verified && <span className="badge active">Verified ✓</span>}
            </div>
          </Field>

          <Field label="Aadhaar Number (optional, 12 digits)" error={errors.aadhaar}>
            <input
              inputMode="numeric"
              maxLength={12}
              value={form.aadhaar}
              onChange={(e) => update("aadhaar", digitsOnly(e.target.value, 12))}
              placeholder="123456789012"
            />
          </Field>
        </div>

        {otpSent && !verified && (
          <div className="form-row">
            <Field label="Enter the 6-digit OTP">
              <div className="otp-row">
                <input
                  inputMode="numeric"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(digitsOnly(e.target.value, 6))}
                  placeholder="123456"
                />
                <button type="button" onClick={verifyOtp} disabled={otpBusy || otp.length !== 6}>
                  {otpBusy ? "Checking…" : "Verify"}
                </button>
              </div>
            </Field>
          </div>
        )}
        {otpMsg && <div className={"msg " + (otpMsg.ok ? "success" : "error")}>{otpMsg.text}</div>}

        <div className="form-row">
          <Field label="Gender *">
            <select value={form.gender} onChange={(e) => update("gender", e.target.value)}>
              <option>Male</option><option>Female</option><option>Other</option>
            </select>
          </Field>
          <Field label="Age * (18-65)" error={errors.age}>
            <input
              type="number" min="18" max="65"
              value={form.age}
              onChange={(e) => update("age", digitsOnly(e.target.value, 2))}
            />
          </Field>
        </div>

        <div className="form-row">
          <Field label="Blood Group *">
            <select value={form.blood_group} onChange={(e) => update("blood_group", e.target.value)}>
              {BLOOD.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </Field>
        </div>

        <h2>Health & Medical</h2>
        <div className="form-row">
          <Field label="Weight (kg, min 45)" error={errors.weight}>
            <input
              type="number" min="30" max="150"
              value={form.weight}
              onChange={(e) => update("weight", e.target.value)}
              placeholder="70"
            />
          </Field>
          <Field label="Previous HB Count (g/dL)" error={errors.previous_hb}>
            <input
              type="number" step="0.1" min="5" max="20"
              value={form.previous_hb}
              onChange={(e) => update("previous_hb", e.target.value)}
              placeholder="14.5"
            />
          </Field>
        </div>

        <div className="form-row">
          <Field label="Diseases">
            <select value={form.diseases} onChange={(e) => update("diseases", e.target.value)}>
              {DISEASES.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </Field>
          <Field label="Bad Habits">
            <select value={form.bad_habits} onChange={(e) => update("bad_habits", e.target.value)}>
              {BAD_HABITS.map((h) => <option key={h} value={h}>{h}</option>)}
            </select>
          </Field>
        </div>

        <div className="form-row">
          <Field label="Disorders">
            <select value={form.disorders} onChange={(e) => update("disorders", e.target.value)}>
              {DISORDERS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </Field>
        </div>

        <h2>Donation History</h2>
        <div className="form-row">
          <Field label="Have you donated blood before? *">
            <select
              value={form.donated_before}
              onChange={(e) => {
                update("donated_before", e.target.value);
                if (e.target.value === "no") update("last_donation_date", "");
              }}
            >
              <option value="no">No, this is my first time</option>
              <option value="yes">Yes, I have donated before</option>
            </select>
          </Field>

          {form.donated_before === "yes" && (
            <Field label="Last Donation Date *" error={errors.last_donation_date}>
              <input
                type="date"
                max={todayStr()}
                value={form.last_donation_date}
                onChange={(e) => update("last_donation_date", e.target.value)}
              />
            </Field>
          )}
        </div>

        {showCooldown && (
          <div className={"msg " + (stillInactive ? "error" : "success")}>
            {stillInactive
              ? "You donated recently, so your profile will be inactive until " + formatDate(nextDate) +
                " (" + cooldownMonths(form.gender) + " month gap)."
              : "You are eligible to donate again. Your profile will be active."}
          </div>
        )}

        <h2>Location</h2>
        <div className="form-row">
          <Field label="City *" error={errors.city}>
            <input value={form.city} onChange={(e) => update("city", e.target.value)} placeholder="Bengaluru" />
          </Field>
          <Field label="Latitude" error={errors.latitude}>
            <input type="number" step="any" value={form.latitude} onChange={(e) => update("latitude", e.target.value)} placeholder="12.9716" />
          </Field>
        </div>
        <div className="form-row">
          <Field label="Longitude" error={errors.longitude}>
            <input type="number" step="any" value={form.longitude} onChange={(e) => update("longitude", e.target.value)} placeholder="77.5946" />
          </Field>
        </div>

        <h2>Consents</h2>
        <div>
          <label>
            <input
              type="checkbox"
              checked={form.sms_consent}
              onChange={(e) => update("sms_consent", e.target.checked)}
            />
            {" "}I consent to receive SMS alerts about blood requests
          </label>
          {errors.sms_consent && <small className="field-error">{errors.sms_consent}</small>}
        </div>

        <div className="full">
          <button type="submit" disabled={loading || !verified}>
            {loading ? "Registering..." : verified ? "Register as Donor" : "Verify phone to register"}
          </button>
        </div>
      </form>
    </div>
  );
}
/* ---------- Blood request ---------- */
export function BloodRequest() {
  return (
    <>
      <h1>Request blood</h1>
      <p className="sub">The doctor ID is used to verify the request before donors are alerted.</p>
      <ApiForm path={() => "/api/requests"} button="Send request"
        okText="Request created. It will be verified, then matching donors are alerted.">
        <label>Patient name<input name="patient_name" required /></label>
        <label>Hospital<input name="hospital_name" required /></label>
        <label>Doctor ID<input name="doctor_id" required /></label>
        <label>Blood group<BloodSelect /></label>
        <label>Units needed<input name="units_needed" type="number" min="1" defaultValue="1" required /></label>
        <label>Priority<select name="priority" defaultValue="normal">
          <option>critical</option><option>urgent</option><option>normal</option>
        </select></label>
        <LocationFields />
      </ApiForm>
    </>
  );
}

/* ---------- Search donors ---------- */
export function SearchDonors() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState(null);
  async function run(form) {
    const p = new URLSearchParams();
    if (form?.blood_group.value) p.set("blood_group", form.blood_group.value);
    if (form?.city.value.trim()) p.set("city", form.city.value.trim());
    try {
      const d = await api("/api/donors" + (p.toString() ? "?" + p : ""));
      setRows(asList(d, "donors"));
      setMsg(null);
    } catch (err) { setMsg({ ok: false, text: err.message }); }
  }
  useEffect(() => { run(null); }, []);
  return (
    <>
      <h1>Find donors</h1>
      <p className="sub">Showing active donors only.</p>
      <div className="card">
        <form onSubmit={(e) => { e.preventDefault(); run(e.target); }}>
          <label>Blood group<BloodSelect any /></label>
          <label>City<input name="city" placeholder="e.g. Mumbai" /></label>
          <div className="full"><button>Search</button></div>
        </form>
      </div>
      <Msg m={msg} />
      <div className="card">
        <Table rows={rows} cols={[["Name", "name"], ["Blood group", "blood_group"], ["City", "city"], ["Gender", "gender"], ["Phone", "phone"]]} />
      </div>
    </>
  );
}
const PRIORITY_RANK = { critical: 0, urgent: 1, normal: 2 };

// Experienced donors (donated before) come first, then the rest
function sortDonors(list) {
  return [...list].sort(
    (a, b) => (b.has_donated_before ? 1 : 0) - (a.has_donated_before ? 1 : 0)
  );
}
/* ---------- Blood bank portal ---------- */
function Login({ onChange }) {
  const [msg, setMsg] = useState(null);
  if (getToken())
    return <div className="card">Logged in. <button className="ghost" onClick={() => { setAuth(null); onChange(); }}>Log out</button></div>;
  async function submit(e) {
    e.preventDefault();
    try {
      const d = await api("/api/auth/login", "POST", formToObject(e.target));
      setAuth(d.token || d.access_token);
      onChange();
    } catch (err) { setMsg({ ok: false, text: err.message }); }
  }
  return (
    <div className="card">
      <form onSubmit={submit}>
        <label>Email<input name="email" type="email" required /></label>
        <label>Password<input name="password" type="password" required /></label>
        <div className="full"><button>Log in</button></div>
      </form>
      <Msg m={msg} />
    </div>
  );
}

export function LoginPage({ go }) {
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const d = await api("/api/auth/login", "POST", formToObject(e.target));
      setAuth(d.token || d.access_token);
      const role = currentUser()?.role;
      go && go(STAFF_ROLES.includes(role) ? "portal" : role === "donor" ? "profile" : "home");
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-copy">
        <h1>Welcome back.</h1>
        <p className="sub">Log in to manage your donor profile, respond to requests, or update your blood bank's stock.</p>
        <ul>
          <li>Donors see their details and cooldown</li>
          <li>Staff record donations and verify requests</li>
          <li>Requesters track their blood requests</li>
        </ul>
      </div>
      <div className="card">
        <h2>Log in</h2>
        <Msg m={msg} />
        <form onSubmit={submit}>
          <label className="full">Email<input name="email" type="email" required autoComplete="email" /></label>
          <label className="full">Password<input name="password" type="password" required autoComplete="current-password" /></label>
          <div className="full"><button disabled={busy}>{busy ? "Logging in…" : "Log in"}</button></div>
        </form>
        <p className="muted center note">
          New here?{" "}
          <button className="link" type="button" onClick={() => go && go("donate")}>Become a donor</button>
        </p>
      </div>
    </div>
  );
}

function Banks() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState(null);
  useEffect(() => {
    api("/api/bloodbank/banks").then((d) => setRows(asList(d, "banks"))).catch((e) => setMsg({ ok: false, text: getToken() ? e.message : "Log in to see the blood bank list." }));
  }, []);
  return <div className="card"><Msg m={msg} /><Table rows={rows} cols={[["ID", "id"], ["Name", "name"], ["City", "city"], ["Phone", "phone"]]} /></div>;
}

export function Portal() {
  const [tab, setTab] = useState(0);
  const [, force] = useState(0);
  const tabs = ["Stock", "Blood banks", "Record donation", "Verify request"];

  const user = currentUser();
  const isStaff = hasStaffAccess(user);

  return (
    <div className="page form-page">
      <div className="form-container">
        <div className="form-header">
          <div className="form-icon" aria-hidden="true">🏥</div>
          <h1>Blood Bank Portal</h1>
          <p>{isStaff ? "Manage blood stock, record donations, and verify requests" : "View blood bank information"}</p>
        </div>

        {!isStaff && (
          <div className="card info-card">
            <div className="info-icon">ℹ️</div>
            <div>
              <h3>Staff Access Required</h3>
              <p>You need to be logged in as <strong>admin, doctor, paramedical staff, or blood bank staff</strong> to access stock management, donation recording, and request verification features.</p>
              <p>Your current role: <strong>{user?.role || "Not logged in"}</strong></p>
            </div>
          </div>
        )}

        <Login onChange={() => { setTab(0); force((n) => n + 1); }} />

        {isStaff && (
          <div className="tabs" role="tablist">
            {tabs.map((t, i) => (
              <button key={t} role="tab" aria-selected={i === tab}
                className={i === tab ? "active on" : ""} onClick={() => setTab(i)}>{t}</button>
            ))}
          </div>
        )}

        {isStaff && tab === 0 && (
          <ApiForm path={() => "/api/bloodbank/stock"} button="Update stock" okText="Stock updated.">
            <label><span className="label-text">Blood bank ID</span><input name="blood_bank_id" type="number" required className="input" /></label>
            <label><span className="label-text">Blood group</span><BloodSelect /></label>
            <label><span className="label-text">Units available</span><input name="units_available" type="number" min="0" required className="input" /></label>
          </ApiForm>
        )}

        {/* Everyone can see the blood bank list; staff see it on the "Blood banks" tab */}
        {(!isStaff || tab === 1) && <Banks />}

        {isStaff && tab === 2 && (
          <ApiForm path={() => "/api/bloodbank/donation"} button="Record donation"
            okText="Donation recorded. Donor is now in cooldown (3 months men, 4 months women).">
            <label><span className="label-text">Donor ID</span><input name="donor_id" type="number" required className="input" /></label>
            <label><span className="label-text">Blood bank ID</span><input name="blood_bank_id" type="number" required className="input" /></label>
            <label><span className="label-text">Donation date</span><input name="donation_date" type="date" required className="input" /></label>
            <label><span className="label-text">Units donated</span><input name="units" type="number" min="1" defaultValue="1" required className="input" /></label>
          </ApiForm>
        )}

        {isStaff && tab === 3 && (
          <ApiForm path={(f) => `/api/requests/${f.request_id.value}/verify`} button="Verify request"
            okText="Request verified. Donors will be alerted.">
            <label><span className="label-text">Request ID</span><input name="request_id" type="number" required className="input" /></label>
          </ApiForm>
        )}
      </div>
    </div>
  );
}

/* ---------- My Profile (editable) ---------- */
export function Profile() {
  const [donor, setDonor] = useState(null);
  const [edit, setEdit] = useState(false);
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api("/api/donors/me")
      .then((d) => {
        setDonor(d);
        setForm({
          name: d.name || "", blood_group: d.blood_group || "O+",
          gender: d.gender || "Male", age: d.age || "", phone: d.phone || "",
          aadhaar: d.aadhaar || "", weight: d.weight || "",
          previous_hb: d.previous_hb || "", diseases: d.diseases || "None",
          bad_habits: d.bad_habits || "None", disorders: d.disorders || "None",
          sms_consent: d.sms_consent ? true : false, city: d.city || "",
          latitude: d.latitude || "", longitude: d.longitude || "",
          last_donation_date: d.last_donation_date || "",
        });
      })
      .catch((e) => setMsg(getToken() ? e.message : "Log in as a donor to see your profile."));
  }, []);

  const update = (k, v) => setForm({ ...form, [k]: v });

  const save = async () => {
    try {
      const res = await api("/api/donors", "POST", {
        ...form,
        weight: form.weight ? Number(form.weight) : null,
        previous_hb: form.previous_hb ? Number(form.previous_hb) : null,
        latitude: form.latitude ? Number(form.latitude) : null,
        longitude: form.longitude ? Number(form.longitude) : null,
        sms_consent: form.sms_consent ? 1 : 0,
      });
      setDonor(res.donor);
      setEdit(false);
      setMsg("Profile updated successfully.");
    } catch (e) {
      setMsg(e.message);
    }
  };

  if (!donor) {
    return (
      <div className="page">
        <h1>My Profile</h1>
        {msg && <div className="msg error">{msg}</div>}
        <div className="card">Loading your profile...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>My Profile</h1>
      {msg && <div className={"msg " + (msg.includes("successfully") ? "success" : "error")}>{msg}</div>}

      {!edit ? (
        <div className="card">
          <p><strong>Name:</strong> {donor.name}</p>
          <p><strong>Blood Group:</strong> {donor.blood_group}</p>
          <p><strong>Gender:</strong> {donor.gender}</p>
          <p><strong>Age:</strong> {donor.age}</p>
          <p><strong>Phone:</strong> {donor.phone}</p>
          <p><strong>Aadhaar:</strong> {donor.aadhaar || "—"}</p>
          <p><strong>Weight:</strong> {donor.weight ? donor.weight + " kg" : "—"}</p>
          <p><strong>Previous HB:</strong> {donor.previous_hb || "—"}</p>
          <p><strong>Diseases:</strong> {donor.diseases || "—"}</p>
          <p><strong>Bad Habits:</strong> {donor.bad_habits || "—"}</p>
          <p><strong>Disorders:</strong> {donor.disorders || "—"}</p>
          <p><strong>City:</strong> {donor.city || "—"}</p>
          <p><strong>Status:</strong> <span className={"badge " + donor.status}>{donor.status}</span></p>
          <p><strong>SMS Consent:</strong> {donor.sms_consent ? "Yes" : "No"}</p>
          <button className="ghost" onClick={() => setEdit(true)}>Edit Profile</button>
        </div>
      ) : (
        <div className="card">
          <h2>Edit Profile</h2>
          <div className="form-row">
            <div><label>Name</label><input value={form.name} onChange={e => update("name", e.target.value)} /></div>
            <div><label>Blood Group</label><select value={form.blood_group} onChange={e => update("blood_group", e.target.value)}>
              {BLOOD.map(b => <option key={b} value={b}>{b}</option>)}
            </select></div>
          </div>
          <div className="form-row">
            <div><label>Gender</label><select value={form.gender} onChange={e => update("gender", e.target.value)}>
              <option>Male</option><option>Female</option><option>Other</option>
            </select></div>
            <div><label>Age</label><input type="number" value={form.age} onChange={e => update("age", e.target.value)} min="18" max="65" /></div>
          </div>
          <div className="form-row">
            <div><label>Phone</label><input value={form.phone} onChange={e => update("phone", e.target.value)} /></div>
            <div><label>Aadhaar</label><input value={form.aadhaar} onChange={e => update("aadhaar", e.target.value)} /></div>
          </div>
          <div className="form-row">
            <div><label>Weight (kg)</label><input type="number" value={form.weight} onChange={e => update("weight", e.target.value)} min="30" max="150" /></div>
            <div><label>Previous HB Count</label><input type="number" step="0.1" value={form.previous_hb} onChange={e => update("previous_hb", e.target.value)} min="5" max="20" /></div>
          </div>
          <div className="form-row">
            <div><label>Diseases</label><select value={form.diseases} onChange={e => update("diseases", e.target.value)}>
              {DISEASES.map(d => <option key={d} value={d}>{d}</option>)}
            </select></div>
            <div><label>Bad Habits</label><select value={form.bad_habits} onChange={e => update("bad_habits", e.target.value)}>
              {BAD_HABITS.map(h => <option key={h} value={h}>{h}</option>)}
            </select></div>
          </div>
          <div className="form-row">
            <div><label>Disorders</label><select value={form.disorders} onChange={e => update("disorders", e.target.value)}>
              {DISORDERS.map(d => <option key={d} value={d}>{d}</option>)}
            </select></div>
            <div><label>City</label><input value={form.city} onChange={e => update("city", e.target.value)} /></div>
          </div>
          <div className="form-row">
            <div><label>Latitude</label><input value={form.latitude} onChange={e => update("latitude", e.target.value)} /></div>
            <div><label>Longitude</label><input value={form.longitude} onChange={e => update("longitude", e.target.value)} /></div>
          </div>
          <div><label>Last Donation Date</label><input type="date" value={form.last_donation_date} onChange={e => update("last_donation_date", e.target.value)} /></div>
          <div>
            <label>
              <input type="checkbox" checked={form.sms_consent} onChange={e => update("sms_consent", e.target.checked)} />
              {" "}I consent to receive SMS alerts
            </label>
          </div>
          <div className="full">
            <button onClick={save}>Save Changes</button>
            <button className="ghost" onClick={() => setEdit(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Hospital inbox (blood bank / hospital staff) ---------- */
export function HospitalInbox() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState(null);
  const user = currentUser();

  async function load() {
    try {
      const d = await api("/api/hospital/inbox");
      setRows(asList(d, "requests"));
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  useEffect(() => { if (hasStaffAccess(user)) load(); }, []);

  async function respond(id, response) {
    try {
      const d = await api("/api/hospital/notices/" + id + "/respond", "POST", { response });
      setMsg({ ok: true, text: d.message });
      load();
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  if (!hasStaffAccess(user)) {
    return (
      <div className="page">
        <h1>Hospital inbox</h1>
        <div className="card">Log in as blood bank or hospital staff to see incoming requests.</div>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Hospital inbox</h1>
      <p className="sub">Blood requests sent to your blood bank. Critical ones come first.</p>
      <Msg m={msg} />

      {rows.length === 0 && <div className="card empty">No requests yet.</div>}

      {rows.map((r) => {
        const enough = r.units_in_stock >= r.units_needed;
        return (
          <div className="card request-card" key={r.notice_id}>
            <div className="request-head">
              <strong>{r.patient_name}</strong>
              <span className={"badge " + r.priority}>{r.priority}</span>
            </div>

            <p>
              Needs <strong>{r.units_needed}</strong> unit(s) of <strong>{r.blood_group}</strong>{" "}
              at {r.hospital_name}
              {r.distance_km != null && " (" + Number(r.distance_km).toFixed(1) + " km from " + r.bank_name + ")"}
            </p>
            <p>
              Your stock: <strong>{r.units_in_stock}</strong> unit(s) {enough ? "(enough)" : "(not enough)"}
            </p>
            <p>
              Status: <strong>{r.notice_status}</strong>
              {!r.verified && " · waiting for verification"}
            </p>

            {r.accepted_donors.length > 0 && (
              <div>
                <strong>Donors who accepted:</strong>
                <ul>
                  {r.accepted_donors.map((d) => (
                    <li key={d.id}>{d.name} ({d.blood_group}), {d.phone}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="full">
              {r.notice_status === "notified" && (
                <>
                  <button onClick={() => respond(r.notice_id, "accepted")}>We can supply</button>
                  <button className="ghost" onClick={() => respond(r.notice_id, "declined")}>Cannot supply</button>
                </>
              )}
              {r.notice_status === "accepted" && (
                <button onClick={() => respond(r.notice_id, "fulfilled")}>Mark fulfilled</button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- My alerts (donor) ---------- */
export function MyAlerts() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState(null);

  async function load() {
    try {
      const d = await api("/api/hospital/my-alerts");
      setRows(asList(d, "alerts"));
    } catch (err) {
      setMsg({ ok: false, text: getToken() ? err.message : "Log in as a donor to see your alerts." });
    }
  }

  useEffect(() => { load(); }, []);

  async function respond(id, response) {
    try {
      const d = await api("/api/hospital/my-alerts/" + id + "/respond", "POST", { response });
      setMsg({ ok: true, text: d.message });
      load();
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  return (
    <div className="page">
      <h1>My alerts</h1>
      <p className="sub">Requests that need your blood group.</p>
      <Msg m={msg} />

      {rows.length === 0 && <div className="card empty">No alerts right now.</div>}

      {rows.map((a) => (
        <div className="card request-card" key={a.alert_id}>
          <div className="request-head">
            <strong>{a.blood_group} needed</strong>
            <span className={"badge " + a.priority}>{a.priority}</span>
          </div>
          <p>
            Please donate at <strong>{a.donate_at || a.hospital_name}</strong>
            {a.city ? ", " + a.city : ""}.
          </p>

          {a.status === "accepted" && <p>You accepted. Thank you!</p>}
          {a.status === "declined" && <p>You declined this request.</p>}

          {(a.status === "sent" || a.status === "delivered" || a.status === "failed") && (
            <div className="full">
              <button onClick={() => respond(a.alert_id, "accepted")}>I will donate</button>
              <button className="ghost" onClick={() => respond(a.alert_id, "declined")}>Cannot donate</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}