import { useEffect, useState } from "react";
import { api, currentUser, hasStaffAccess } from "./api";

const Msg = ({ m }) =>
  m ? <div className={"msg " + (m.ok ? "ok" : "err")}>{m.text}</div> : null;

const BloodSelect = ({ name, value, onChange }) => (
  <select name={name} value={value} onChange={onChange}>
    {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((b) => (
      <option key={b} value={b}>{b}</option>
    ))}
  </select>
);

export function HospitalInbox() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState(null);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [donorMessages, setDonorMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [replyForm, setReplyForm] = useState({ request_id: null, donor_id: null, message: "" });
  const user = currentUser();

  async function load() {
    try {
      const d = await api("/api/hospital/inbox");
      setRows(asList(d, "requests"));
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  useEffect(() => {
    if (hasStaffAccess(user)) load();
  }, [user]);

  async function respond(notice_id, response) {
    try {
      const d = await api("/api/hospital/notices/" + notice_id + "/respond", "POST", { response });
      setMsg({ ok: true, text: d.message });
      load();
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  async function viewDonorMessages(request_id) {
    setLoading(true);
    try {
      const d = await api("/api/requests/donor-messages/hospital/" + request_id);
      setDonorMessages(d);
      setSelectedRequest(request_id);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function sendReply(e) {
    e.preventDefault();
    try {
      const d = await api("/api/hospital/reply-donor", "POST", replyForm);
      setMsg({ ok: true, text: d.message });
      setReplyForm({ request_id: null, donor_id: null, message: "" });
      viewDonorMessages(replyForm.request_id);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  if (!hasStaffAccess(user)) {
    return (
      <div className="page">
        <h1>Hospital Inbox</h1>
        <div className="card">Log in as blood bank or hospital staff to see incoming requests.</div>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Hospital Inbox</h1>
      <p className="sub">Blood requests sent to your hospital/blood bank. Critical ones come first.</p>
      <Msg m={msg} />

      {/* Donor Messages Modal */}
      {selectedRequest && (
        <div className="modal-overlay" onClick={() => { setSelectedRequest(null); setDonorMessages([]); }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => { setSelectedRequest(null); setDonorMessages([]); }}>×</button>
            <h3>Donor Responses for Request #{selectedRequest}</h3>
            {loading ? <p>Loading...</p> : donorMessages.length === 0 ? (
              <p className="muted">No donor responses yet.</p>
            ) : (
              <div className="donor-messages-list">
                {donorMessages.map(m => (
                  <div key={m.id} className="card donor-message-card">
                    <div className="message-header">
                      <strong>{m.donor_name}</strong>
                      <span className="badge blood">{m.donor_bg}</span>
                      <span className="badge {m.status}">{m.status}</span>
                    </div>
                    <p className="muted">{m.donor_city} · {m.donor_phone}</p>
                    {m.donor_message && (
                      <div className="message-content">
                        <strong>Message:</strong> {m.donor_message}
                      </div>
                    )}
                    <div className="reply-form">
                      <form onSubmit={sendReply}>
                        <input type="hidden" name="request_id" value={m.request_id} onChange={e => setReplyForm(f => ({...f, request_id: m.request_id}))} />
                        <input type="hidden" name="donor_id" value={m.donor_id} onChange={e => setReplyForm(f => ({...f, donor_id: m.donor_id}))} />
                        <textarea
                          name="message"
                          rows="2"
                          placeholder="Reply to donor..."
                          value={replyForm.message}
                          onChange={e => setReplyForm(f => ({...f, message: e.target.value}))}
                        />
                        <button type="submit" className="sm">Send Reply</button>
                      </form>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {rows.length === 0 && <div className="card empty">No requests yet.</div>}

      {rows.map((r) => {
        const enough = r.units_in_stock >= r.units_needed;
        return (
          <div className="card request-card" key={r.notice_id}>
            <div className="request-head">
              <div>
                <strong>{r.patient_name}</strong>
                <span className="muted"> · Request #{r.request_id}</span>
              </div>
              <span className={"badge " + r.priority}>{r.priority}</span>
            </div>

            <div className="request-details">
              <div className="detail-row">
                <label>Blood Group:</label>
                <span><strong>{r.blood_group}</strong> · {r.units_needed} unit(s) needed</span>
              </div>
              <div className="detail-row">
                <label>Hospital:</label>
                <span>{r.hospital_name}</span>
              </div>
              <div className="detail-row">
                <label>Doctor:</label>
                <span>{r.doctor_id || '—'}</span>
              </div>
              <div className="detail-row">
                <label>Nurse/Paramedic:</label>
                <span>{r.nurse_id || r.paramedic_id || '—'}</span>
              </div>
              <div className="detail-row">
                <label>Your Stock:</label>
                <span className={enough ? "ok" : "low"}>
                  {r.units_in_stock} unit(s) {enough ? "(enough)" : "(not enough)"}
                </span>
              </div>
              <div className="detail-row">
                <label>Distance:</label>
                <span>{r.distance_km ? r.distance_km + " km from " + r.bank_name : "Unknown"}</span>
              </div>
              <div className="detail-row">
                <label>Status:</label>
                <span><strong>{r.notice_status}</strong> {!r.verified && "· waiting for verification"}</span>
              </div>
            </div>

            {r.accepted_donors.length > 0 && (
              <div className="accepted-donors">
                <strong>Donors who accepted:</strong>
                <ul>
                  {r.accepted_donors.map((d) => (
                    <li key={d.id}>{d.name} ({d.blood_group}), {d.phone}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="request-actions">
              {r.notice_status === "notified" && (
                <>
                  <button onClick={() => respond(r.notice_id, "accepted")}>We can supply</button>
                  <button className="ghost" onClick={() => respond(r.notice_id, "declined")}>Cannot supply</button>
                </>
              )}
              {r.notice_status === "accepted" && (
                <button onClick={() => respond(r.notice_id, "fulfilled")}>Mark fulfilled</button>
              )}
              <button className="ghost" onClick={() => viewDonorMessages(r.request_id)}>
                View Donor Messages ({r.accepted_donors.length})
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Helper to extract array from API response
function asList(data, key) {
  if (Array.isArray(data)) return data;
  if (data && data[key]) return data[key];
  return [];
}