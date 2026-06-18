export default function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`tfw-pulse rounded ${className}`}
      style={{ background: "var(--surface-3)" }}
    />
  );
}
