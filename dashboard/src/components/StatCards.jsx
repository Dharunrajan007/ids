export default function StatCards({ stats }) {
  const cards = [
    { label: "Total flows", value: stats?.total_flows, tone: "" },
    { label: "Normal", value: stats?.normal_count, tone: "tone-normal" },
    { label: "Attacks", value: stats?.attack_count, tone: "tone-attack" },
  ];
  return (
    <div className="stat-cards">
      {cards.map((card) => (
        <div key={card.label} className={`card stat-card ${card.tone}`}>
          <span className="stat-label">{card.label}</span>
          <span className="stat-value">
            {typeof card.value === "number" ? card.value.toLocaleString() : "—"}
          </span>
        </div>
      ))}
    </div>
  );
}
