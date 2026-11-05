import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchJson } from "../api/client";
import PageShell from "../components/PageShell";
import { num } from "../components/Money";

export default function BiPage({ tool, range, onRange }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const title = tool === "redash" ? "Redash" : "Tableau";

  useEffect(() => {
    setError(null);
    fetchJson(`/api/bi/${tool}`, range)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [tool, range.from, range.to]);

  return (
    <PageShell
      title={title}
      subtitle="Weekly active users, views per user, and most consumed dashboards / workbooks"
      from={range.from}
      to={range.to}
      onRange={onRange}
    >
      {error ? <div className="error">{error}</div> : null}
      {!data && !error ? <div className="loading">Loading…</div> : null}
      {data ? (
        <div className="grid">
          <div className="card">
            <h2>Active users by week</h2>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={data.active_users_weekly}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="active_users" fill="#0b6bcb" name="Active users" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid cols-2">
            <div className="card">
              <h2>Views by user</h2>
              <table>
                <thead>
                  <tr>
                    <th>Week</th>
                    <th>User</th>
                    <th>Views</th>
                  </tr>
                </thead>
                <tbody>
                  {data.users_weekly.slice(0, 20).map((row) => (
                    <tr key={`${row.week}-${row.user_name}`}>
                      <td>{row.week}</td>
                      <td>{row.user_name}</td>
                      <td>{num(row.view_count, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card">
              <h2>Most consumed {tool === "redash" ? "dashboards" : "views"}</h2>
              <table>
                <thead>
                  <tr>
                    <th>Week</th>
                    <th>Name</th>
                    <th>Views</th>
                  </tr>
                </thead>
                <tbody>
                  {data.objects_weekly.slice(0, 20).map((row) => (
                    <tr key={`${row.week}-${row.object_id}`}>
                      <td>{row.week}</td>
                      <td>{row.object_name || row.object_id}</td>
                      <td>{num(row.view_count, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </PageShell>
  );
}
