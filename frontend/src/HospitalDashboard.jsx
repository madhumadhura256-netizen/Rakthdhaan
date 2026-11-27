import { useEffect, useState } from "react";
import { api, getToken, currentUser } from "./api";

const Msg = ({ m }) =>
  m ? <div className={"msg " + (m.ok ? "ok" : "err")}>{m.text}</div> : null;

const BloodSelect = ({ name, value, onChange }) => (
  <select name={name} value={value} onChange={onChange}>
    {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((b) => (
      <option key={b} value={b}>{b}</option>
    ))}
  </select>
);

function StockItem({ bg, current, onUpdate }) {
  const [val, setVal] = useState(current);
  useEffect(() => setVal(current), [current]);
  return (
    <div className="stock-item">
      <label>
        <span className="bg-badge">{bg}</span>
        <input type="number" min="0" max="999" value={val}
          onChange={(e) => setVal(Math.max(0, Number(e.target.value) || 0))} />
        <button type="button" className="sm" onClick={() => onUpdate(bg, val)} disabled={val === current}>
          Update
        </button>
      </label>
    </div>
  );
}

export function HospitalDashboard({ go }) {
  const [tab, setTab] = useState(0);
  const [hospital, setHospital] = useState(null);
  const [stock, setStock] = useState([]);
  const [msg, setMsg] = useState(null);
  const [smsHistory, setSmsHistory] = useState([]);
  const [nearbyDonors, setNearbyDonors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [smsForm, setSmsForm] = useState({ blood_group: "O+", radius_km: 20, message: "" });
  const [donorSearch, setDonorSearch] = useState({ blood_group: "O+", radius_km: 20, city: "" });

  const tabs = ["Overview", "Blood Stock", "Send SMS", "SMS History", "Nearby Donors"];

  useEffect(() => {
    loadHospital();
  }, []);

  async function loadHospital() {
    try {
      const d = await api("/api/hospital/my-profile");
      setHospital(d);
      loadStock(d.id);
      loadSmsHistory(d.id);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  async function loadStock(hospitalId) {
    try {
      const d = await api("/api/hospital/stock");
      setStock(d);
    } catch (err) {
      console.error(err);
    }
  }

  async function loadSmsHistory(hospitalId) {
    try {
      const d = await api("/api/hospital/sms-history");
      setSmsHistory(d);
    } catch (err) {
      console.error(err);
    }
  }

  async function updateStock(blood_group, units_available) {
    try {
      const d = await api("/api/hospital/stock", "POST", { blood_group, units_available });
      setMsg({ ok: true, text: d.message });
      loadStock(hospital?.id);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  async function sendBulkSms(e) {
    e.preventDefault();
    setMsg(null);
    setLoading(true);
    try {
      const d = await api("/api/hospital/send-sms", "POST", smsForm);
      setMsg({ ok: true, text: d.message });
      setSmsForm({ ...smsForm, message: "" });
      loadSmsHistory(hospital?.id);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function searchNearbyDonors(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("blood_group", donorSearch.blood_group);
      params.set("radius_km", donorSearch.radius_km);
      if (donorSearch.city) params.set("city", donorSearch.city);
      const d = await api("/api/hospital/nearby-donors?" + params.toString());
      setNearbyDonors(d);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setLoading(false);
    }
  }

  if (!hospital) {
    return (
      <div className="page">
        <h1>Hospital Dashboard</h1>
        <div className="card">Loading...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="dash-header">
        <div>
          <h1>Hospital Dashboard</h1>
          <p className="sub">
            {hospital.name} <span className="badge verified">Verified</span>
            <span className="hospital-id">ID: {hospital.hospital_id}</span>
          </p>
        </div>
      </div>

      <Msg m={msg} />

      <div className="tabs" role="tablist">
        {tabs.map((t, i) => (
          <button
            key={t}
            role="tab"
            aria-selected={i === tab}
            className={i === tab ? "active" : ""}
            onClick={() => { setTab(i); setMsg(null); setNearbyDonors([]); }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* OVERVIEW */}
      {tab === 0 && (
        <div>
          <div className="dash-grid">
            <div className="card stat-card">
              <h3>Blood Stock</h3>
              <p className="big-num">{stock.filter(s => s.units_available > 0).length} / 8</p>
              <p className="muted">Blood types available</p>
            </div>
            <div className="card stat-card">
              <h3>Total Units</h3>
              <p className="big-num">{stock.reduce((a, s) => a + (s.units_available || 0), 0)}</p>
              <p className="muted">Units in inventory</p>
            </div>
            <div className="card stat-card">
              <h3>SMS Sent</h3>
              <p className="big-num">{smsHistory.length}</p>
              <p className="muted">Campaigns run</p>
            </div>
            <div className="card stat-card">
              <h3>Total Donors Reached</h3>
              <p className="big-num">{smsHistory.reduce((a, s) => a + (s.donors_count || 0), 0)}</p>
              <p className="muted">Across all campaigns</p>
            </div>
          </div>

          <div className="card">
          <h3>Current Blood Stock</h3>
          {stock.length === 0 ? (
            <p className="muted">No stock records yet. Add stock in the Blood Stock tab.</p>
          ) : (
            <table>
              <thead><tr><th>Blood Group</th><th>Units Available</th><th>Last Updated</th></tr></thead>
              <tbody>
                {stock.map(s => (
                  <tr key={s.blood_group}>
                    <td><strong>{s.blood_group}</strong></td>
                    <td className={s.units_available > 0 ? "ok" : "low"}>{s.units_available}</td>
                    <td>{new Date(s.last_updated).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      )}

      {/* BLOOD STOCK MANAGEMENT */}
      {tab === 1 && (
        <div className="card">
          <h3>Update Blood Stock</h3>
          <p className="muted">Set units available for each blood group. Set to 0 if out of stock.</p>
          <div className="stock-grid">
            {["A+","A-","B+","B-","AB+","AB-","O+","O-"].map((bg) => (
  <StockItem key={bg} bg={bg}
    current={stock.find((s) => s.blood_group === bg)?.units_available || 0}
    onUpdate={updateStock} />
))}
          </div>
        </div>
      )}

      {/* SEND SMS */}
      {tab === 2 && (
        <form className="card" onSubmit={sendBulkSms}>
          <h3>Send SMS to Nearby Donors</h3>
          <p className="muted">Sends SMS to all eligible donors (active, SMS consent, mobile verified, not in cooldown) within radius.</p>
          <Msg m={msg} />
          <div className="form-row">
            <label>Blood Group *<BloodSelect name="blood_group" value={smsForm.blood_group} onChange={e => setSmsForm({...smsForm, blood_group: e.target.value})} /></label>
            <label>Radius (km) *<input type="number" min="1" max="100" value={smsForm.radius_km} onChange={e => setSmsForm({...smsForm, radius_km: Number(e.target.value)})} /></label>
          </div>
          <label>
            Custom Message (optional)
            <textarea
              name="message"
              rows="3"
              value={smsForm.message}
              onChange={e => setSmsForm({...smsForm, message: e.target.value})}
              placeholder="Default: URGENT: [Hospital] needs [Blood Group] blood donors. Please contact [Phone] to donate. - Raktdhan"
            />
          </label>
          <div className="full">
            <button type="submit" disabled={loading}>
              {loading ? "Sending..." : "Send SMS to Nearby Donors"}
            </button>
          </div>
        </form>
      )}

      {/* SMS HISTORY */}
      {tab === 3 && (
        <div className="card">
          <h3>SMS Campaign History</h3>
          {smsHistory.length === 0 ? (
            <p className="muted">No SMS campaigns sent yet.</p>
          ) : (
            <table>
              <thead><tr><th>Date</th><th>Blood Group</th><th>Donors Reached</th><th>Status</th><th>Message Preview</th></tr></thead>
              <tbody>
                {smsHistory.map(s => (
                  <tr key={s.id}>
                    <td>{new Date(s.sent_at).toLocaleString()}</td>
                    <td><strong>{s.blood_group}</strong></td>
                    <td>{s.donors_count}</td>
                    <td><span className={"badge " + s.status}>{s.status}</span></td>
                    <td className="msg-preview">{s.message.substring(0, 60)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* NEARBY DONORS */}
      {tab === 4 && (
        <div className="card">
          <h3>Find Nearby Eligible Donors</h3>
          <p className="muted">Shows donors with matching blood group who are active, have SMS consent, mobile verified, and not in cooldown.</p>
          <form onSubmit={searchNearbyDonors} className="search-form">
            <div className="form-row">
              <label>Blood Group *<BloodSelect name="blood_group" value={donorSearch.blood_group} onChange={e => setDonorSearch({...donorSearch, blood_group: e.target.value})} /></label>
              <label>Radius (km) *<input type="number" min="1" max="100" value={donorSearch.radius_km} onChange={e => setDonorSearch({...donorSearch, radius_km: Number(e.target.value)})} /></label>
              <label>City (optional)<input value={donorSearch.city} onChange={e => setDonorSearch({...donorSearch, city: e.target.value})} placeholder="Filter by city" /></label>
            </div>
            <div className="full"><button type="submit" disabled={loading}>{loading ? "Searching..." : "Search Donors"}</button></div>
          </form>

          {nearbyDonors.length > 0 && (
              <div>
                <p className="result-count">Found {nearbyDonors.length} eligible donors</p>
                <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th><th>Blood Group</th><th>Age</th><th>City</th>
                      <th>Distance</th><th>Phone</th><th>Total Donated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nearbyDonors.map(d => (
                      <tr key={d.id}>
                        <td>{d.name}</td>
                        <td><strong>{d.blood_group}</strong></td>
                        <td>{d.age}</td>
                        <td>{d.city}</td>
                        <td>{d.distance_km ? d.distance_km + " km" : "N/A"}</td>
                        <td>{d.phone}</td>
                        <td>{d.total_units_donated || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}