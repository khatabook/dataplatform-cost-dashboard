export default function DateRange({ from, to, onChange }) {
  return (
    <div className="range">
      <label>
        From
        <input
          type="date"
          value={from}
          onChange={(e) => onChange({ from: e.target.value, to })}
        />
      </label>
      <label>
        To
        <input
          type="date"
          value={to}
          onChange={(e) => onChange({ from, to: e.target.value })}
        />
      </label>
    </div>
  );
}
