import { attackMeta, confidencePercent } from "../utils/format.js";

export default function DetailPanel({ record, onClose }) {
  if (!record) {
    return (
      <div className="card detail-card">
        <h2>Details</h2>
        <p className="empty-note">
          Select a row in the live feed or an alert to inspect it.
        </p>
      </div>
    );
  }
  const attack = record.prediction === "attack";
  const features = record.features ?? {};
  return (
    <div className="card detail-card">
      <div className="detail-head">
        <h2>Details</h2>
        <button type="button" className="detail-close" onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="detail-verdict">
        <span className={`badge badge-big ${attack ? "badge-attack" : "badge-normal"}`}>
          {attack ? `ATTACK · ${attackMeta(record.attack_type).label}` : "NORMAL"}
        </span>
      </div>
      <dl className="detail-meta">
        <dt>Confidence</dt>
        <dd>
          {confidencePercent(record.confidence)}
          <span className="caveat">
            {" "}model probability — uncalibrated, not a correctness guarantee
          </span>
        </dd>
        <dt>Timestamp</dt>
        <dd className="mono">{record.timestamp ?? "—"}</dd>
      </dl>
      <h3>Submitted features ({Object.keys(features).length})</h3>
      <div className="feature-scroll">
        <table className="feature-table">
          <tbody>
            {Object.entries(features).map(([name, value]) => (
              <tr key={name}>
                <td className="mono feature-name">{name}</td>
                <td className="mono">{String(value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
