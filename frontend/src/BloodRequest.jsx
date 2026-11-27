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

export function BloodRequest() {
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [myRequests, setMyRequests] = useState([]);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [donorResponses, setDonorResponses] = useState([]);
  const [replyForm, setReplyForm] = useState({ request_id: null, message: "" });
  const user = currentUser();

  useEffect(() => {
    if (getToken()) loadMyRequests();
  }, [getToken()]);

  async function loadMyRequests() {
    try {
      const d = await api("/api/requests/my");
      setMyRequests(d);
    } catch (err) {
      console.error(err);
    }
  }

  async function createRequest(e) {
    e.preventDefault();
    setMsg(null);
    setLoading(true);
    try {
      const form = e.target;
      const formData = new FormData(form);
      const body = Object.fromEntries(formData);
      body.units_needed = Number(body.units_needed);
      body.latitude = body.latitude ? Number(body.latitude) : null;
      body.longitude = body.longitude ? Number(body.longitude) : null;

      // Add staff IDs if available
      if (user?.role === 'doctor' || user?.role === 'paramedical' || user?.role === 'nurse') {
        body.doctor_id = body.doctor_id || (user.role === 'doctor' ? `DOC${user.user_id}` : '');
        body.nurse_id = body.nurse_id || (user.role === 'nurse' ? `NUR${user.user_id}` : '');
        body.paramedic_id = body.paramedic_id || (user.role === 'paramedical' ? `PAR${user.user_id}` : '');
      }

      const d = await api("/api/requests", "POST", body);
      setMsg({ ok: true, text: d.message });
      form.reset();
      loadMyRequests();
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function viewDonorResponses(request_id) {
    try {
      const d = await api("/api/requests/donor-messages/hospital/" + request_id);
      setDonorResponses(d);
      setSelectedRequest(request_id);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  async function sendReply(e) {
    e.preventDefault();
    try {
      const d = await api("/api/requests/donor-message", "POST", replyForm);
      setMsg({ ok: true, text: d.message });
      setReplyForm({ ...replyForm, message: "" });
      viewDonorResponses(replyForm.request_id);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  return (
    <>
      <h1>Request Blood</h1>
      <p className="sub">
        {user?.role === 'donor'
          ? "Fill in the details below. Your request will be verified before donors are alerted."
          : "Fill in the details below. Staff requests are auto-verified and donors are alerted immediately."
        }
      </p>

      <Msg m={msg} />

      <form className="card" onSubmit={createRequest}>
        <label>Patient name<input name="patient_name" required /></label>
        <label>Hospital<input name="hospital_name" required /></label>
        <label>Doctor ID<input name="doctor_id" required placeholder="e.g., DOC001" /></label>
        <label>Nurse ID (optional)<input name="nurse_id" placeholder="e.g., NUR001" /></label>
        <label>Paramedic ID (optional)<input name="paramedic_id" placeholder="e.g., PAR001" /></label>
        <label>Blood group<BloodSelect name="blood_group" required /></label>
        <label>Units needed<input name="units_needed" type="number" min="1" defaultValue="1" required /></label>
        <label>Priority<select name="priority" defaultValue="normal">
          <option>critical</option><option>urgent</option><option>normal</option>
        </select></label>
        <LocationFields />
        <div className="full"><button disabled={loading}>{loading ? "Submitting..." : "Send request"}</button></div>
      </form>

      {myRequests.length > 0 && (
        <div className="card">
          <h3>My Requests</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Patient</th><th>Blood Group</th><th>Units</th><th>Priority</th><th>Status</th><th>Verified</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {myRequests.map(r => (
                  <tr key={r.id}>
                    <td>{r.patient_name}</td>
                    <td><strong>{r.blood_group}</strong></td>
                    <td>{r.units_needed}</td>
                    <td><span className={"badge " + r.priority}>{r.priority}</span></td>
                    <td>{r.status}</td>
                    <td>{r.verified ? "✓ Yes" : "✗ No"}</td>
                    <td>
                      <button className="ghost sm" onClick={() => viewDonorResponses(r.id)}>
                        View Donor Responses
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Donor Responses Modal */}
      {selectedRequest && (
        <div className="modal-overlay" onClick={() => { setSelectedRequest(null); setDonorResponses([]); }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => { setSelectedRequest(null); setDonorResponses([]); }}>×</button>
            <h3>Donor Responses for Request #{selectedRequest}</h3>
            {donorResponses.length === 0 ? (
              <p className="muted">No donor responses yet.</p>
            ) : (
              <div className="donor-messages-list">
                {donorResponses.map(d => (
                  <div key={d.id} className="card donor-message-card">
                    <div className="message-header">
                      <strong>{d.donor_name}</strong>
                      <span className="badge blood">{d.donor_bg}</span>
                      <span className="badge {d.status}">{d.status}</span>
                    </div>
                    <p className="muted">{d.donor_city} · {d.donor_phone}</p>
                    {d.donor_message && (
                      <div className="message-content">
                        <strong>Donor Message:</strong> {d.donor_message}
                      </div>
                    )}
                    {d.hospital_reply && (
                      <div className="message-content reply">
                        <strong>Hospital Reply:</strong> {d.hospital_reply}
                      </div>
                    )}
                    <div className="reply-form">
                      <form onSubmit={sendReply}>
                        <input type="hidden" name="request_id" value={selectedRequest} />
                        <input type="hidden" name="donor_id" value={d.donor_id} />
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
    </>
  );
}