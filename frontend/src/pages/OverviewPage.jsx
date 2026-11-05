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

export default function OverviewPage({ range, onRange }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    fetchJson("/api/overview", range)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [range.from, range.to]);

  const total = (data?.series || []).reduce((sum, row) => sum + (row.total_usd || 0), 0);

  return (
    <PageShell
      title="Overview"
      subtitle="Stored daily cost across Snowflake, Kubecost services, and Rudderstack S3 PUT"
      from={range.from}
      to={range.to}
      onRange={onRange}
    >
      {error ? <div className="error">{error}</div> : null}
      {!data && !error ? <div className="loading">Loading…</div> : null}
      {data ? (
        <div className="grid">
          <div className="grid cols-3">
            <div className="card">
              <div className="metric">
                {usd(total)}
                <span>Total in range</span>
              </div>
            </div>
            <div className="card">
              <div className="metric">
                {usd(data.credit_usd)}
                <span>Snowflake credit USD rate</span>
              </div>
            </div>
            <div className="card">
              <div className="metric">
                {data.series.length}
                <span>Days with data</span>
              </div>
            </div>
          </div>
          <div className="card">
            <h2>Daily cost stack</h2>
            <div style={{ width: "100%", height: 340 }}>
              <ResponsiveContainer>
                <AreaChart data={data.series}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => usd(v)} />
                  <Legend />
                  <Area type="monotone" dataKey="snowflake_usd" stackId="1" stroke="#0b6bcb" fill="#0b6bcb" name="Snowflake" />
                  <Area type="monotone" dataKey="airflow_usd" stackId="1" stroke="#1b7f4c" fill="#1b7f4c" name="Airflow" />
                  <Area type="monotone" dataKey="rudderstack_usd" stackId="1" stroke="#a15c00" fill="#a15c00" name="Rudderstack" />
                  <Area type="monotone" dataKey="redash_usd" stackId="1" stroke="#7c3aed" fill="#7c3aed" name="Redash" />
                  <Area type="monotone" dataKey="rudderstack_s3_put_usd" stackId="1" stroke="#b42318" fill="#b42318" name="S3 PUT" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : null}
    </PageShell>
  );
}
