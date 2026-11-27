import { useEffect, useState } from "react";
import { api, currentUser, hasStaffAccess } from "./api";

const Msg = ({ m }) =>
  m ? <div className={"msg " + (m.ok ? "ok" : "err")}>{m.text}</div> : null;

export function AdminHospitalVerification() {
  const [pending, setPending] = useState([]);
  const [all, setAll] = useState([]);
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewDoc, setViewDoc] = useState(null);
  const [tab, setTab] = useState(0);
  const user = currentUser();

  if (!user || user.role !== "admin") {
    return (
      <div className="page">
        <h1>Admin: Hospital Verification</h1>
        <div className="card">Admin access required.</div>
      </div>
    );
  }

  useEffect(() => {
    loadPending();
    loadAll();
  }, []);

  async function loadPending() {
    try {
      const d = await api("/api/hospital/admin/pending");
      setPending(d);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  async function loadAll() {
    try {
      const d = await api("/api/hospital/admin/all");
      setAll(d);
    } catch (err) {
      console.error(err);
    }
  }

  async function verify(hospitalId, approved) {
    setLoading(true);
    try {
      const d = await api("/api/hospital/admin/" + hospitalId + "/verify", "POST", {
        verified: approved,
        notes: "",
      });
      setMsg({ ok: true, text: d.message });
      loadPending();
      loadAll();
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <h1>Hospital Verification</h1>
      <Msg m={msg} />

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === 0} className={tab === 0 ? "active" : ""} onClick={() => setTab(0)}>
          Pending ({pending.length})
        </button>
        <button role="tab" aria-selected={tab === 1} className={tab === 1 ? "active" : ""} onClick={() => setTab(1)}>
          All Hospitals
        </button>
      </div>

      {tab === 0 && (
        <div className="hospital-list">
          {pending.length === 0 ? (
            <div className="card empty">No pending hospital registrations.</div>
          ) : (
            pending.map(h => (
              <div key={h.id} className="card hospital-card">
                <div className="hospital-header">
                  <div>
                    <h3>{h.name}</h3>
                    <p className="muted">Requested Hospital ID: <strong>{h.hospital_id}</strong></p>
                  </div>
                  <span className="badge pending">Pending</span>
                </div>

                <div className="hospital-details">
                  <div className="detail-grid">
                    <div><label>Address</label><p>{h.address}, {h.city} - {h.pincode}</p></div>
                    <div><label>Phone</label><p>{h.phone}</p></div>
                    <div><label>Email</label><p>{h.email}</p></div>
                    <div><label>License Number</label><p>{h.license_number}</p></div>
                    <div><label>User Email</label><p>{h.user_email}</p></div>
                    <div><label>User Phone</label><p>{h.user_phone}</p></div>
                  </div>

                  <div className="doc-section">
                    <label>License Document:</label>
                    {h.license_document && (
                      <div className="doc-actions">
                        {h.license_document.startsWith("data:application/pdf") ? (
                          <>
                            <iframe src={h.license_document} title="License" />
                            <button className="ghost" onClick={() => setViewDoc(h.license_document)}>Open Full</button>
                          </>
                        ) : (
                          <>
                            <img src={h.license_document} alt="License" />
                            <button className="ghost" onClick={() => setViewDoc(h.license_document)}>Open Full</button>
                          </>
                        )}
                      </div>
                    )}
                    {!h.license_document && <p className="muted">No document uploaded</p>}
                  </div>

                  <div className="verify-actions">
                    <button className="success" onClick={() => verify(h.id, true)} disabled={loading}>
                      Verify & Approve
                    </button>
                    <button className="danger" onClick={() => verify(h.id, false)} disabled={loading}>
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 1 && (
        <div className="card">
          <h3>All Hospitals</h3>
          {all.length === 0 ? (
            <p className="muted">No hospitals registered.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Hospital ID</th><th>Name</th><th>City</th><th>Status</th>
                    <th>Verified By</th><th>Verified At</th><th>User Email</th>
                  </tr>
                </thead>
                <tbody>
                  {all.map(h => (
                    <tr key={h.id}>
                      <td>{h.hospital_id}</td>
                      <td>{h.name}</td>
                      <td>{h.city}</td>
                      <td><span className={"badge " + (h.verified ? "verified" : "pending")}>{h.verified ? "Verified" : "Pending"}</span></td>
                      <td>{h.verified_by || "-"}</td>
                      <td>{h.verified_at ? new Date(h.verified_at).toLocaleDateString() : "-"}</td>
                      <td>{h.user_email}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {viewDoc && (
        <div className="modal-overlay" onClick={() => setViewDoc(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setViewDoc(null)}>×</button>
            {viewDoc.startsWith("data:application/pdf") ? (
              <iframe src={viewDoc} title="License Document" style={{width: "100%", height: "600px", border: "none"}} />
            ) : (
              <img src={viewDoc} alt="License Document" style={{maxWidth: "100%", maxHeight: "600px"}} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}