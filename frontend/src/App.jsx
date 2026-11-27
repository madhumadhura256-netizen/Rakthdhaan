import { useEffect, useState } from "react";
import {
  Home, LoginPage, DonorRegister, BloodRequest, SearchDonors, Portal, DonorProfile,
  HospitalInbox, MyAlerts,
  currentUser, setAuth,
} from "./pages";

import { HospitalRegister } from "./HospitalRegister";
import { HospitalDashboard } from "./HospitalDashboard";
import { AdminHospitalVerification } from "./AdminHospitalVerification";

const VIEWS = {
  home: Home,
  login: LoginPage,
  donate: DonorRegister,
  request: BloodRequest,
  search: SearchDonors,
  portal: Portal,
  profile: DonorProfile,
  hospital: HospitalInbox,
  alerts: MyAlerts,
  hospital_register: HospitalRegister,
  hospital_dashboard: HospitalDashboard,
  admin_hospitals: AdminHospitalVerification,
};

const STAFF_ROLES = ["admin", "doctor", "paramedical", "blood_connect", "nurse"];

// Roles that can see the Hospital Inbox link (staff + hospital accounts)
const INBOX_ROLES = [...STAFF_ROLES, "hospital"];

const ROLE_LABELS = {
  admin: "Admin",
  doctor: "Doctor",
  paramedical: "Paramedical staff",
  nurse: "Nurse",
  blood_connect: "Blood bank staff",
  donor: "Donor",
  requester: "Requester",
  hospital: "Hospital",
  blood_bank: "Blood Bank",
};

function Drop() {
  return (
    <svg viewBox="0 0 22 28" aria-hidden="true">
      <path d="M11 1C11 1 2 12 2 18a9 9 0 0 0 18 0C20 12 11 1 11 1Z" fill="#c1122f" />
    </svg>
  );
}

export default function App() {
  const [page, setPage] = useState("home");
  const [, force] = useState(0);

  // Re-render when someone logs in or out
  useEffect(() => {
    const refresh = () => force((n) => n + 1);
    window.addEventListener("auth-change", refresh);
    return () => window.removeEventListener("auth-change", refresh);
  }, []);

  const user = currentUser();
  const View = VIEWS[page] || Home;

  const go = (key) => {
    setPage(key);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const links = [
    ["home", "Home"],
    ["search", "Find donors"],
    ["request", "Request blood"],
    ["portal", "Blood bank portal"],
  ];

  if (user?.role === "donor") {
    links.push(["profile", "My profile"]);
    links.push(["alerts", "My alerts"]);
  }

  // Hospital Inbox: staff AND hospital accounts
  if (INBOX_ROLES.includes(user?.role)) {
    links.push(["hospital", "Hospital Inbox"]);
  }

  // Hospital-specific navigation
  if (user?.role === "hospital") {
    links.push(["hospital_dashboard", "Hospital Dashboard"]);
  }

  // Admin-specific navigation
  if (user?.role === "admin") {
    links.push(["admin_hospitals", "Verify Hospitals"]);
  }

  return (
    <>
      <header className="nav">
        <div className="nav-inner">
          <button className="brand" onClick={() => go("home")} aria-label="Raktdhan home">
            <Drop /> Raktdhan
          </button>

          <nav className="nav-links" aria-label="Main">
            {links.map(([key, label]) => (
              <button
                key={key}
                className={"nav-link" + (key === page ? " on" : "")}
                onClick={() => go(key)}
              >
                {label}
              </button>
            ))}
          </nav>

          <div className="nav-user">
            {user ? (
              <>
                <span className="role-chip">{ROLE_LABELS[user.role] || user.role}</span>
                <button
                  className="ghost sm"
                  onClick={() => { setAuth(null); go("home"); }}
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <button className="ghost sm" onClick={() => go("login")}>Log in</button>
                <button className="sm" onClick={() => go("donate")}>Become a donor</button>
                <button className="ghost sm" onClick={() => go("hospital_register")}>Register Hospital</button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="container">
        <div className={"view" + (page === "home" ? "" : " narrow")} key={page}>
          <View go={go} />
        </div>
      </main>

      <footer className="footer">
        Raktdhan connects blood donors, patients and blood banks.
      </footer>
    </>
  );
}