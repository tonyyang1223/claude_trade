import { COLORS } from '../theme';
// 通用格式化工具（金额 / 百分比 / 数字）。

export function fmtMcap(v: number | null | undefined): string {
  if (v == null) return '-';
  const abs = Math.abs(v);
  if (abs >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function fmtPct(v: number | null | undefined, withSign = true): string {
  if (v == null) return '-';
  const s = v.toFixed(2) + '%';
  return withSign && v > 0 ? `+${s}` : s;
}

export function fmtNum(v: number | null | undefined): string {
  if (v == null) return '-';
  return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export function fmtPrice(v: number | null | undefined): string {
  if (v == null) return '-';
  if (Math.abs(v) >= 1) return `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  return `$${v.toPrecision(4)}`;
}

export function colorForChange(v: number | null | undefined): string {
  if (v == null || v === 0) return COLORS.sub;
  return v > 0 ? '#f6465d' : '#2ebd85';
}
