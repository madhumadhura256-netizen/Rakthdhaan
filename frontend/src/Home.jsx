import { useEffect, useState } from "react";
import { api, asList, getToken, BLOOD } from "./api";

/* ---------- small helpers ---------- */
const Msg = ({ m }) =>
  m ? <div className={"msg " + (m.ok ? "ok" : "err")}>{m.text}</div> : null;

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
  const [topDonors, setTopDonors] = useState([]);
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
    // Fetch top donors
    api("/api/donors/top-donors?limit=10")
      .then((d) => setTopDonors(d))
      .catch(() => {}); // Silently fail for top donors
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

      {/* TOP DONORS LEADERBOARD */}
      {topDonors.length > 0 && (
        <section className="leaderboard-section">
          <h2 className="section-title">Top Donors</h2>
          <p className="sub">Most units donated — verified by certificate codes</p>
          <div className="leaderboard">
            {topDonors.map((donor, idx) => (
              <div key={donor.id} className="leaderboard-item">
                <div className="rank {idx < 3 ? 'top-three' : ''}">
                  {idx + 1}
                </div>
                <div className="donor-info">
                  <div className="donor-name">{donor.name}</div>
                  <div className="donor-meta">
                    <span className="blood-badge">{donor.blood_group}</span>
                    <span className="city">{donor.city}</span>
                  </div>
                </div>
                <div className="donor-units">
                  <span className="units">{donor.total_units_donated}</span>
                  <span className="units-label">units</span>
                </div>
              </div>
            ))}
          </div>
        </section>
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