import { NavLink, Route, Routes } from "react-router-dom";
import { useMemo, useState } from "react";
import { defaultRange } from "./api/client";
import OverviewPage from "./pages/OverviewPage";
import SnowflakePage from "./pages/SnowflakePage";
import RudderstackPage from "./pages/RudderstackPage";
import AirflowPage from "./pages/AirflowPage";
import BiPage from "./pages/BiPage";

const links = [
  { to: "/", label: "Overview", end: true },
  { to: "/snowflake", label: "Snowflake" },
  { to: "/rudderstack", label: "Rudderstack" },
  { to: "/airflow", label: "Airflow" },
  { to: "/redash", label: "Redash" },
  { to: "/tableau", label: "Tableau" },
];

export default function App() {
  const initial = useMemo(() => defaultRange(), []);
  const [range, setRange] = useState(initial);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">Dataplatform<br />Cost Dashboard</div>
        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? "active" : undefined)}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<OverviewPage range={range} onRange={setRange} />} />
          <Route path="/snowflake" element={<SnowflakePage range={range} onRange={setRange} />} />
          <Route path="/rudderstack" element={<RudderstackPage range={range} onRange={setRange} />} />
          <Route path="/airflow" element={<AirflowPage range={range} onRange={setRange} />} />
          <Route path="/redash" element={<BiPage tool="redash" range={range} onRange={setRange} />} />
          <Route path="/tableau" element={<BiPage tool="tableau" range={range} onRange={setRange} />} />
        </Routes>
      </main>
    </div>
  );
}
