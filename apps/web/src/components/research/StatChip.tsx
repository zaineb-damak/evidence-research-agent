// A single labeled statistic below the progress stepper (sources found,
// claims extracted, running cost). Deliberately not a dot-joined string —
// each stat is its own discrete, labeled chip.

interface StatChipProps {
  label: string;
  value: string;
}

export function StatChip({ label, value }: StatChipProps) {
  return (
    <div className="stat-chip">
      <span className="stat-chip__value">{value}</span>
      <span className="stat-chip__label">{label}</span>
    </div>
  );
}
