import { useState } from "react";

import AlertsList from "./components/AlertsList.jsx";
import AttackTypesChart from "./components/AttackTypesChart.jsx";
import DetailPanel from "./components/DetailPanel.jsx";
import Header from "./components/Header.jsx";
import LiveFeed from "./components/LiveFeed.jsx";
import StatCards from "./components/StatCards.jsx";
import TimelineChart from "./components/TimelineChart.jsx";
import usePolling from "./hooks/usePolling.js";
import { fetchHealth, fetchRecentFeed, fetchStats } from "./services/api.js";

// ADR-007: the dashboard POLLS — no WebSockets. /stats and the feed every
// 2 s; /health every 10 s (the model never changes mid-run, so hitting it at
// feed cadence would be pointless traffic).
const POLL_MS = 2000;
const HEALTH_POLL_MS = 10000;

export default function App() {
  const health = usePolling(fetchHealth, HEALTH_POLL_MS);
  const stats = usePolling(fetchStats, POLL_MS);
  const recent = usePolling(fetchRecentFeed, POLL_MS);
  const [selected, setSelected] = useState(null);

  const disconnected = Boolean(stats.error || recent.error || health.error);
  const loading = !disconnected && stats.data === null;

  return (
    <div className="app">
      <Header health={health.data} disconnected={disconnected} />

      {disconnected && (
        <div className="banner banner-error" role="alert">
          API unreachable — retrying every {POLL_MS / 1000} s.
          {stats.data && " Showing the last data received."}
          {" "}Start it with: <code>python -m uvicorn api.main:app --port 8000</code>
        </div>
      )}
      {loading && (
        <div className="banner banner-info">Connecting to the prediction API…</div>
      )}

      <StatCards stats={stats.data} />

      <div className="grid-main">
        <div className="col-left">
          <TimelineChart timeline={stats.data?.traffic_timeline} />
          <LiveFeed
            records={recent.data}
            selected={selected}
            onSelect={setSelected}
          />
        </div>
        <div className="col-right">
          <AttackTypesChart attacksByType={stats.data?.attacks_by_type} />
          <AlertsList
            records={recent.data}
            selected={selected}
            onSelect={setSelected}
          />
          <DetailPanel record={selected} onClose={() => setSelected(null)} />
        </div>
      </div>

      <footer className="footer">
        College IDS project · M6 dashboard · detection only, no prevention ·
        confidence values are uncalibrated model probabilities
      </footer>
    </div>
  );
}
