import { useEffect, useState } from "react";
import { api, getToken, currentUser, setAuth, BLOOD, DISEASES, BAD_HABITS, DISORDERS } from "./api";

const Msg = ({ m }) =>
  m ? <div className={"msg " + (m.ok ? "ok" : "err")}>{m.text}</div> : null;

export function DonorProfile({ go }) {
  const [donor, setDonor] = useState(null);
  const [edit, setEdit] = useState(false);
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState("");
  const [certCode, setCertCode] = useState("");
  const [certMsg, setCertMsg] = useState(null);
  const [certLoading, setCertLoading] = useState(false);

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

  const verifyCertificate = async (e) => {
    e.preventDefault();
    if (!certCode.trim()) {
      setCertMsg({ ok: false, text: "Enter a certificate code" });
      return;
    }
    setCertLoading(true);
    setCertMsg(null);
    try {
      const d = await api("/api/donors/verify-certificate", "POST", { certificate_code: certCode.trim().toUpperCase() });
      setCertMsg({ ok: true, text: d.message });
      setCertCode("");
      // Refresh donor data
      const updated = await api("/api/donors/me");
      setDonor(updated);
    } catch (err) {
      setCertMsg({ ok: false, text: err.message });
    } finally {
      setCertLoading(false);
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
        <div className="profile-view">
          <div className="profile-header">
            <div className="profile-avatar">{donor.name?.charAt(0) || "D"}</div>
            <div>
              <h2>{donor.name}</h2>
              <p className="sub">
                <span className="badge blood">{donor.blood_group}</span>
                <span className="badge status">{donor.status}</span>
                {donor.is_rare_group && <span className="badge rare">Rare Group</span>}
              </p>
            </div>
          </div>

          {/* Donation Stats */}
          <div className="stats-row">
            <div className="stat-card">
              <div className="stat-value">{donor.total_units_donated || 0}</div>
              <div className="stat-label">Total Units Donated</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{donor.donation_codes ? (typeof donor.donation_codes === 'string' ? JSON.parse(donor.donation_codes).length : donor.donation_codes.length) : 0}</div>
              <div className="stat-label">Verified Donations</div>
            </div>
          </div>

          {/* Certificate Verification */}
          <div className="card cert-section">
            <h3>Add Donation Certificate</h3>
            <p className="muted">After donating blood, you receive a certificate code (format: RKT-YYYY-XXXXXX). Enter it here to verify and add to your donation count.</p>
            <form onSubmit={verifyCertificate} className="cert-form">
              <div className="form-row">
                <input
                  type="text"
                  value={certCode}
                  onChange={e => setCertCode(e.target.value.toUpperCase())}
                  placeholder="RKT-2024-ABC123"
                  maxLength={16}
                  style={{textTransform: "uppercase"}}
                />
                <button type="submit" disabled={certLoading}>
                  {certLoading ? "Verifying..." : "Verify & Add"}
                </button>
              </div>
              {certMsg && <div className={"msg " + (certMsg.ok ? "ok" : "err")}>{certMsg.text}</div>}
            </form>

            {donor.donation_codes && (
              <div className="cert-list">
                <h4>Verified Certificates</h4>
                <ul>
                  {(typeof donor.donation_codes === 'string' ? JSON.parse(donor.donation_codes) : donor.donation_codes).map((code, i) => (
                    <li key={i}><code>{code}</code></li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Profile Details */}
          <div className="card">
            <h3>Personal Details</h3>
            <div className="detail-grid">
              <div><label>Blood Group</label><p>{donor.blood_group}</p></div>
              <div><label>Gender</label><p>{donor.gender}</p></div>
              <div><label>Age</label><p>{donor.age}</p></div>
              <div><label>Phone</label><p>{donor.phone}</p></div>
              <div><label>Aadhaar</label><p>{donor.aadhaar || "—"}</p></div>
              <div><label>Weight</label><p>{donor.weight ? donor.weight + " kg" : "—"}</p></div>
              <div><label>Previous HB</label><p>{donor.previous_hb || "—"}</p></div>
              <div><label>City</label><p>{donor.city || "—"}</p></div>
              <div><label>SMS Consent</label><p>{donor.sms_consent ? "Yes" : "No"}</p></div>
              <div><label>Last Donation</label><p>{donor.last_donation_date || "Never"}</p></div>
              <div><label>Status</label><p><span className={"badge " + donor.status}>{donor.status}</span></p></div>
            </div>
          </div>

          <div className="health-section">
            <h3>Medical History</h3>
            <div className="detail-grid">
              <div><label>Diseases</label><p>{donor.diseases || "—"}</p></div>
              <div><label>Bad Habits</label><p>{donor.bad_habits || "—"}</p></div>
              <div><label>Disorders</label><p>{donor.disorders || "—"}</p></div>
            </div>
          </div>

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