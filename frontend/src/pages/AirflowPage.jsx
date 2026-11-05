import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchJson } from "../api/client";
import PageShell from "../components/PageShell";
import { usd } from "../components/Money";

export default function AirflowPage({ range, onRange }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    fetchJson("/api/airflow", range)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [range.from, range.to]);

  const total = (data?.series || []).reduce((sum, row) => sum + (row.total_usd || 0), 0);

  return (
    <PageShell
      title="Airflow"
      subtitle="Kubecost infrastructure cost for the Airflow service"
      from={range.from}
      to={range.to}
      onRange={onRange}
    >
      {error ? <div className="error">{error}</div> : null}
      {!data && !error ? <div className="loading">Loading…</div> : null}
      {data ? (
        <div className="grid">
          <div className="card">
            <div className="metric">
              {usd(total)}
              <span>Total Airflow infra in range</span>
            </div>
          </div>
          <div className="card">
            <h2>Daily cost by component</h2>
            <div style={{ width: "100%", height: 340 }}>
              <ResponsiveContainer>
                <AreaChart data={data.series}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => usd(v)} />
                  <Legend />
                  <Area type="monotone" dataKey="cpu_usd" stackId="1" fill="#0b6bcb" stroke="#0b6bcb" name="CPU" />
                  <Area type="monotone" dataKey="ram_usd" stackId="1" fill="#1b7f4c" stroke="#1b7f4c" name="RAM" />
                  <Area type="monotone" dataKey="pv_usd" stackId="1" fill="#a15c00" stroke="#a15c00" name="PV" />
                  <Area type="monotone" dataKey="network_usd" stackId="1" fill="#7c3aed" stroke="#7c3aed" name="Network" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : null}
    </PageShell>
  );
}
