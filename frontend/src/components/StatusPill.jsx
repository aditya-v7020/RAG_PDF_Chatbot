export default function StatusPill({ ok, okLabel = "Ready", warnLabel = "API key missing" }) {
  const classes = ok
    ? "bg-green-100 text-green-800"
    : "bg-amber-100 text-amber-800";

  return (
    <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${classes}`}>
      {ok ? okLabel : warnLabel}
    </span>
  );
}
