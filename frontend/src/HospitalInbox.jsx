import { useEffect, useState } from "react";
import { api, currentUser } from "./api";

const INBOX_ROLES = ["admin", "hospital", "doctor", "paramedical", "blood_connect", "nurse"];

const Msg = ({ m }) =>
  m ? <div className={"msg " + (m.ok ? "ok" : "err")}>{m.text}</div> : null;

// Helper to extract array from API response
function asList(data, key) {
  if (Array.isArray(data)) return data;
  if (data && data[key]) return data[key];
  return [];
}

function ReplyBox({ requestId, donorId, onSent, onError }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      const d = await api("/api/hospital/reply-donor", "POST", {
        request_id: requestId,
        donor_id: donorId,
        message: text.trim(),
      });
      setText("");
      onSent(d.message || "Reply sent.");
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="reply-form">
      <form onSubmit={send}>
        <textarea
          rows="2"
          placeholder="Reply to donor..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" className="sm" disabled={busy || !text.trim()}>
          {busy ? "Sending..." : "Send Reply"}
        </button>
      </form>
    </div>
  );
}

export function HospitalInbox() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState(null);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [donorMessages, setDonorMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const user = currentUser();
  const role = user?.role;
  const allowed = INBOX_ROLES.includes(role);

  async function load() {
    try {
      const d = await api("/api/hospital/inbox");
      setRows(asList(d, "requests"));
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  // Depend on the role string, not the user object (a new object every render)
  useEffect(() => {
    if (allowed) load();
  }, [role]);

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
    setSelectedRequest(request_id);
    try {
      const d = await api("/api/hospital/donor-messages/" + request_id);
      setDonorMessages(asList(d, "messages"));
    } catch (err) {
      setMsg({ ok: false, text: err.message });
      setSelectedRequest(null);
    } finally {
      setLoading(false);
    }
  }

  function closeModal() {
    setSelectedRequest(null);
    setDonorMessages([]);
  }

  if (!allowed) {
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
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>×</button>
            <h3>Donor Responses for Request #{selectedRequest}</h3>
            {loading ? (
              <p>Loading...</p>
            ) : donorMessages.length === 0 ? (
              <p className="muted">No donor responses yet.</p>
            ) : (
              <div className="donor-messages-list">
                {donorMessages.map((m) => (
                  <div key={m.id} className="card donor-message-card">
                    <div className="message-header">
                      <strong>{m.donor_name}</strong>
                      <span className="badge blood">{m.donor_bg}</span>
                      <span className={"badge " + (m.status || "")}>{m.status}</span>
                    </div>
                    <p className="muted">{m.donor_city} · {m.donor_phone}</p>
                    {m.donor_message && (
                      <div className="message-content">
                        <strong>Message:</strong> {m.donor_message}
                      </div>
                    )}
                    <ReplyBox
                      requestId={m.request_id ?? selectedRequest}
                      donorId={m.donor_id}
                      onSent={(text) => { setMsg({ ok: true, text }); viewDonorMessages(selectedRequest); }}
                      onError={(text) => setMsg({ ok: false, text })}
                    />
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
        const accepted = r.accepted_donors || [];
        const requestId = r.request_id ?? r.notice_id;
        return (
          <div className="card request-card" key={r.notice_id}>
            <div className="request-head">
              <div>
                <strong>{r.patient_name}</strong>
                <span className="muted"> · Request #{requestId}</span>
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
                <span>{r.doctor_id || "—"}</span>
              </div>
              <div className="detail-row">
                <label>Nurse/Paramedic:</label>
                <span>{r.nurse_id || r.paramedic_id || "—"}</span>
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

            {accepted.length > 0 && (
              <div className="accepted-donors">
                <strong>Donors who accepted:</strong>
                <ul>
                  {accepted.map((d) => (
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
              <button className="ghost" onClick={() => viewDonorMessages(requestId)}>
                View Donor Messages ({accepted.length})
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}