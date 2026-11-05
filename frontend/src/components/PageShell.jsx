import DateRange from "./DateRange";

export default function PageShell({ title, subtitle, from, to, onRange, children }) {
  return (
    <div>
      <div className="toolbar">
        <div>
          <h1>{title}</h1>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        <DateRange from={from} to={to} onChange={onRange} />
      </div>
      {children}
    </div>
  );
}
