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
import { num, usd } from "../components/Money";

export default function RudderstackPage({ range, onRange }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    fetchJson("/api/rudderstack", range)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [range.from, range.to]);

  return (
    <PageShell
      title="Rudderstack"
      subtitle="Infra cost, S3 event volume and PUT spend, Snowflake / CleverTap pipelines"
      from={range.from}
      to={range.to}
      onRange={onRange}
    >
      {error ? <div className="error">{error}</div> : null}
      {!data && !error ? <div className="loading">Loading…</div> : null}
      {data ? (
        <div className="grid">
          <div className="card">
            <h2>Infrastructure cost</h2>
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <AreaChart data={data.infra}>
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

          <div className="card">
            <h2>Weekly S3 volume and PUT cost</h2>
            <table>
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Bucket</th>
                  <th>PUT requests</th>
                  <th>Bytes</th>
                  <th>PUT USD</th>
                </tr>
              </thead>
              <tbody>
                {data.s3_weekly.map((row) => (
                  <tr key={`${row.week}-${row.bucket}`}>
                    <td>{row.week}</td>
                    <td className="mono">{row.bucket}</td>
                    <td>{num(row.put_requests, 0)}</td>
                    <td>{num(row.bytes, 0)}</td>
                    <td>{usd(row.put_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h2>Pipelines to Snowflake / CleverTap</h2>
            <table>
              <thead>
                <tr>
                  <th>Day</th>
                  <th>DAG</th>
                  <th>Destination</th>
                  <th>Events</th>
                  <th>Airflow state</th>
                </tr>
              </thead>
              <tbody>
                {data.pipelines.slice(0, 40).map((row) => (
                  <tr key={`${row.day}-${row.dag_id}`}>
                    <td>{row.day}</td>
                    <td className="mono">{row.dag_id}</td>
                    <td>{row.destination}</td>
                    <td>{row.events == null ? "—" : num(row.events, 0)}</td>
                    <td className={`status-${row.airflow_state === "success" ? "ok" : "error"}`}>
                      {row.airflow_state || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </PageShell>
  );
}
