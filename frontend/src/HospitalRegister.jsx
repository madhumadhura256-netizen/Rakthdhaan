import { useEffect, useState } from "react";
import { api, formToObject, getToken, setToken, BLOOD } from "./api";

const Msg = ({ m }) =>
  m ? <div className={"msg " + (m.ok ? "ok" : "err")}>{m.text}</div> : null;

const BloodSelect = ({ any }) => (
  <select name="blood_group" required={!any}>
    {any && <option value="">Any</option>}
    {BLOOD.map((b) => <option key={b}>{b}</option>)}
  </select>
);

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
      <label>Pincode<input name="pincode" maxLength="6" /></label>
      <label>Latitude<input name="latitude" type="number" step="any" required /></label>
      <label>Longitude<input name="longitude" type="number" step="any" required /></label>
      <div className="full">
        <button type="button" className="ghost" onClick={fill}>Use my current location</button>
      </div>
    </>
  );
}

export function HospitalRegister({ go }) {
  const [form, setForm] = useState({
    name: "",
    address: "",
    city: "",
    pincode: "",
    latitude: "",
    longitude: "",
    phone: "",
    email: "",
    license_number: "",
    license_document: null,
  });
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [docPreview, setDocPreview] = useState(null);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setMsg({ ok: false, text: "File too large (max 5MB)" });
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      setForm((f) => ({ ...f, license_document: ev.target.result }));
      setDocPreview(ev.target.result);
    };
    reader.readAsDataURL(file);
  };

  const validate = () => {
    const errors = {};
    if (!form.name.trim()) errors.name = "Hospital name required";
    if (!form.address.trim()) errors.address = "Address required";
    if (!form.city.trim()) errors.city = "City required";
    if (!form.pincode.trim() || !/^\d{6}$/.test(form.pincode)) errors.pincode = "Valid 6-digit pincode required";
    if (!form.latitude || !form.longitude) errors.location = "Latitude & longitude required";
    if (!form.phone.trim() || !/^[6-9]\d{9}$/.test(form.phone.replace(/\D/g, ""))) errors.phone = "Valid 10-digit mobile required";
    if (!form.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.email)) errors.email = "Valid email required";
    if (!form.license_number.trim()) errors.license_number = "License number required";
    if (!form.license_document) errors.license_document = "License document required (PDF/image, max 5MB)";
    return errors;
  };

  const submit = async (e) => {
    e.preventDefault();
    setMsg(null);
    const errors = validate();
    if (Object.keys(errors).length > 0) {
      setMsg({ ok: false, text: "Please fix the highlighted fields" });
      return;
    }
    setLoading(true);
    try {
      const payload = {
        name: form.name.trim(),
        address: form.address.trim(),
        city: form.city.trim(),
        pincode: form.pincode.trim(),
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        phone: form.phone.replace(/\D/g, ""),
        email: form.email.trim().toLowerCase(),
        license_number: form.license_number.trim(),
        license_document: form.license_document,
      };
      const d = await api("/api/hospital/register", "POST", payload);
      setMsg({ ok: true, text: d.message });
      setForm({
        name: "", address: "", city: "", pincode: "", latitude: "", longitude: "",
        phone: "", email: "", license_number: "", license_document: null,
      });
      setDocPreview(null);
      setTimeout(() => go && go("login"), 2000);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h1>Hospital Registration</h1>
      <p className="sub">Register your hospital to manage blood inventory and alert nearby donors. Verification by admin required.</p>
      <Msg m={msg} />

      <form className="card" onSubmit={submit} noValidate>
        <h2>Hospital Details</h2>
        <div className="form-row">
          <label>Hospital Name *<input value={form.name} onChange={e => update("name", e.target.value)} placeholder="City General Hospital" /></label>
          <label>License Number *<input value={form.license_number} onChange={e => update("license_number", e.target.value)} placeholder="HOSP-LIC-12345" /></label>
        </div>

        <h2>Address & Location</h2>
        <label>Full Address *<textarea name="address" value={form.address} onChange={e => update("address", e.target.value)} rows="2" placeholder="123 Main Road, Near Metro Station" /></label>
        <LocationFields />
        <div className="form-row">
          <label>Phone *<input type="tel" inputMode="numeric" maxLength={10} value={form.phone} onChange={e => update("phone", e.target.value.replace(/\D/g, "").slice(0, 10))} placeholder="9876543210" /></label>
          <label>Email *<input type="email" value={form.email} onChange={e => update("email", e.target.value)} placeholder="bloodbank@hospital.com" /></label>
        </div>

        <h2>License Document</h2>
        <label>
          Upload Hospital License / Registration Certificate (PDF, JPG, PNG - max 5MB) *
          <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={handleFileChange} />
        </label>
        {docPreview && (
          <div className="doc-preview">
            <p>Preview:</p>
            {docPreview.startsWith("data:application/pdf") ? (
              <iframe src={docPreview} title="License Document" />
            ) : (
              <img src={docPreview} alt="License Document" />
            )}
          </div>
        )}

        <div className="full">
          <button type="submit" disabled={loading}>
            {loading ? "Submitting..." : "Submit for Verification"}
          </button>
        </div>
      </form>

      <div className="card info-card">
        <h3>What happens next?</h3>
        <ul>
          <li>Admin reviews your registration and license document</li>
          <li>Once verified, you receive a unique Hospital ID (e.g., HOSP-0001)</li>
          <li>You can then manage blood stock and send SMS alerts to nearby donors</li>
        </ul>
      </div>
    </div>
  );
}