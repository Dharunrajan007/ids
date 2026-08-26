import { alertsFrom, attackMeta, confidencePercent, sameRecord, timeOfDay } from "../utils/format.js";

const MAX_ALERTS = 8;

export default function AlertsList({ records, selected, onSelect }) {
  const alerts = alertsFrom(records).slice(0, MAX_ALERTS);
  return (
    <div className="card alerts-card">
      <h2>
        Attack alerts
        {alerts.length > 0 && <span className="alert-count">{alerts.length}</span>}
      </h2>
      {alerts.length === 0 ? (
        <p className="empty-note">No attacks in the recent window.</p>
      ) : (
        <ul className="alert-list">
          {alerts.map((alert, index) => {
            const meta = attackMeta(alert?.attack_type);
            return (
              <li key={`${alert?.timestamp}-${index}`}>
                <button
                  type="button"
                  className={`alert-item ${sameRecord(alert, selected) ? "alert-selected" : ""}`}
                  onClick={() => onSelect(alert)}
                >
                  <span className="alert-type" style={{ color: meta.color }}>
                    ▮ {meta.label}
                  </span>
                  <span className="mono alert-when">{timeOfDay(alert?.timestamp)}</span>
                  <span className="mono">{confidencePercent(alert?.confidence)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
