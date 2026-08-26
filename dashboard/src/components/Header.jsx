export default function Header({ health, disconnected }) {
  const online = !disconnected && health?.status === "ok" && health?.model_loaded;
  return (
    <header className="header">
      <div>
        <h1>
          <span className="header-shield">⛨</span> IDS Dashboard
        </h1>
        <p className="header-sub">
          NSL-KDD network flow classification · times shown in UTC
        </p>
      </div>
      <div className="header-status">
        {health?.model_version && (
          <span className="model-version" title="From /health — the serialized pipeline the API loaded">
            model {health.model_version}
          </span>
        )}
        <span className={`status-pill ${online ? "status-online" : "status-offline"}`}>
          <span className="status-dot" />
          {online ? "API online" : "API offline"}
        </span>
      </div>
    </header>
  );
}
