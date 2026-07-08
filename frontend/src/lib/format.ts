/** Human-friendly interval labels for scheduled-task UI. */

export function formatInterval(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  if (s % 604800 === 0 && s >= 604800) {
    const w = s / 604800;
    return w === 1 ? "1w" : `${w}w`;
  }
  if (s % 86400 === 0 && s >= 86400) {
    const d = s / 86400;
    return d === 1 ? "1d" : `${d}d`;
  }
  if (s % 3600 === 0 && s >= 3600) {
    const h = s / 3600;
    return h === 1 ? "1h" : `${h}h`;
  }
  if (s % 60 === 0 && s >= 60) {
    const m = s / 60;
    return m === 1 ? "1m" : `${m}m`;
  }
  if (s >= 60) {
    const m = Math.round(s / 60);
    return `${m}m`;
  }
  return `${s}s`;
}

/** Longer phrase for table display, e.g. "every 6h", "daily". */
export function formatIntervalPhrase(seconds: number): string {
  const label = formatInterval(seconds);
  if (label === "1d") return "daily";
  if (label === "1w") return "weekly";
  return `every ${label}`;
}

/** Format a unix-second timestamp for the table. */
export function formatUnixTime(ts: number | null | undefined): string {
  if (ts == null || ts <= 0) return "—";
  try {
    return new Date(ts * 1000).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export function truncateText(text: string, max = 60): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}
