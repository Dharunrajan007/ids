import { attackMeta, confidencePercent, sameRecord, timeOfDay } from "../utils/format.js";

const FEED_ROWS = 15;

export default function LiveFeed({ records, selected, onSelect }) {
  const rows = Array.isArray(records) ? records.slice(0, FEED_ROWS) : [];
  return (
    <div className="card feed-card">
      <h2>Live feed</h2>
      {rows.length === 0 ? (
        <p className="empty-note">Waiting for traffic — POST flows to /predict.</p>
      ) : (
        <table className="feed-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Verdict</th>
              <th>Category</th>
              <th>Service</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((record, index) => {
              const attack = record?.prediction === "attack";
              return (
                <tr
                  key={`${record?.timestamp}-${index}`}
                  className={`${attack ? "row-attack" : ""} ${sameRecord(record, selected) ? "row-selected" : ""}`}
                  onClick={() => onSelect(record)}
                >
                  <td className="mono">{timeOfDay(record?.timestamp)}</td>
                  <td>
                    <span className={`badge ${attack ? "badge-attack" : "badge-normal"}`}>
                      {attack ? "ATTACK" : "normal"}
                    </span>
                  </td>
                  <td>{attack ? attackMeta(record?.attack_type).label : "—"}</td>
                  <td className="mono">{record?.features?.service ?? "—"}</td>
                  <td className="mono">{confidencePercent(record?.confidence)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
