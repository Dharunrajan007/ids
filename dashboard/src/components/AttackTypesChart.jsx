import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { buildTypeChartData } from "../utils/format.js";

export default function AttackTypesChart({ attacksByType }) {
  const data = buildTypeChartData(attacksByType);
  const total = data.reduce((sum, row) => sum + row.count, 0);
  return (
    <div className="card chart-card">
      <h2>Attacks by category</h2>
      {total === 0 ? (
        <p className="empty-note">No attacks detected yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#233046" />
            <XAxis dataKey="label" stroke="#7d8aa5" fontSize={12} />
            <YAxis allowDecimals={false} stroke="#7d8aa5" fontSize={12} />
            <Tooltip
              cursor={{ fill: "#1b273c" }}
              contentStyle={{ background: "#101a2b", border: "1px solid #2a3a55" }}
              labelStyle={{ color: "#c6d2e5" }}
            />
            <Bar dataKey="count" name="Flows">
              {data.map((row) => (
                <Cell key={row.type} fill={row.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
