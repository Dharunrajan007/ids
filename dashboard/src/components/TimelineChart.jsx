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

import { buildTimelineData } from "../utils/format.js";

export default function TimelineChart({ timeline }) {
  const data = buildTimelineData(timeline);
  return (
    <div className="card chart-card">
      <h2>Traffic per minute</h2>
      {data.length === 0 ? (
        <p className="empty-note">No traffic yet — waiting for flows.</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#233046" />
            <XAxis dataKey="minute" stroke="#7d8aa5" fontSize={12} />
            <YAxis allowDecimals={false} stroke="#7d8aa5" fontSize={12} />
            <Tooltip
              contentStyle={{ background: "#101a2b", border: "1px solid #2a3a55" }}
              labelStyle={{ color: "#c6d2e5" }}
            />
            <Legend />
            <Area type="monotone" dataKey="normal" name="Normal" stackId="1"
                  stroke="#2dd4a0" fill="#2dd4a066" />
            <Area type="monotone" dataKey="attack" name="Attack" stackId="1"
                  stroke="#f0433c" fill="#f0433c66" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
