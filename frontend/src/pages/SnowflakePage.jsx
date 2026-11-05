import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchJson } from "../api/client";
import PageShell from "../components/PageShell";
import { num } from "../components/Money";

export default function SnowflakePage({ range, onRange }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    fetchJson("/api/snowflake", range)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [range.from, range.to]);

  const teamChart = useMemo(() => {
    if (!data) return [];
    const weeks = [...new Set(data.team_weekly.map((r) => r.week))];
    const teams = [...new Set(data.team_weekly.map((r) => r.team))];
    return weeks.map((week) => {
      const row = { week };
      for (const team of teams) {
        row[team] = data.team_weekly.find((r) => r.week === week && r.team === team)?.credits || 0;
      }
      return row;
    });
  }, [data]);

  const teams = data ? [...new Set(data.team_weekly.map((r) => r.team))] : [];
  const colors = ["#0b6bcb", "#1b7f4c", "#a15c00", "#7c3aed", "#b42318", "#0f766e"];

  return (
    <PageShell
      title="Snowflake"
      subtitle="Team credits, expensive and long-running queries, Cortex Code"
      from={range.from}
      to={range.to}
      onRange={onRange}
    >
      {error ? <div className="error">{error}</div> : null}
      {!data && !error ? <div className="loading">Loading…</div> : null}
      {data ? (
        <div className="grid">
          <div className="card">
            <h2>Team credits by week</h2>
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <BarChart data={teamChart}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  {teams.map((team, i) => (
                    <Bar key={team} dataKey={team} stackId="a" fill={colors[i % colors.length]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid cols-2">
            <div className="card">
              <h2>Expensive queries</h2>
              <table>
                <thead>
                  <tr>
                    <th>Day</th>
                    <th>User / job</th>
                    <th>Credits</th>
                  </tr>
                </thead>
                <tbody>
                  {data.expensive_queries.slice(0, 15).map((q) => (
                    <tr key={`${q.day}-${q.query_id}`}>
                      <td>{q.day}</td>
                      <td>
                        <div>{q.user_name}</div>
                        <div className="muted mono">{q.job_tag || q.warehouse}</div>
                      </td>
                      <td>{num(q.credits, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card">
              <h2>Long-running queries</h2>
              <table>
                <thead>
                  <tr>
                    <th>Day</th>
                    <th>User / job</th>
                    <th>Seconds</th>
                  </tr>
                </thead>
                <tbody>
                  {data.long_running_queries.slice(0, 15).map((q) => (
                    <tr key={`${q.day}-${q.query_id}`}>
                      <td>{q.day}</td>
                      <td>
                        <div>{q.user_name}</div>
                        <div className="muted mono">{q.job_tag || q.warehouse}</div>
                      </td>
                      <td>{num(q.seconds, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h2>Cortex Code credits by user</h2>
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Token credits</th>
                </tr>
              </thead>
              <tbody>
                {data.cortex.map((row) => (
                  <tr key={row.user_name}>
                    <td>{row.user_name}</td>
                    <td>{num(row.token_credits, 2)}</td>
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
