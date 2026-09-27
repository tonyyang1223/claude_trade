import type { ReactNode } from 'react';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { COLORS } from '../../theme';

interface Props {
  label: string;
  value: ReactNode;
  delta?: number;
  deltaFormatter?: (v: number) => string;
  accent?: string;
}

/** KPI 卡片：标签 + 大数值 + 可选涨跌（红涨绿跌）。 */
export default function KpiCard({ label, value, delta, deltaFormatter, accent = COLORS.text }: Props) {
  const deltaColor = delta === undefined ? undefined : delta >= 0 ? COLORS.up : COLORS.down;
  const deltaText =
    delta !== undefined ? (deltaFormatter ? deltaFormatter(delta) : `${delta >= 0 ? '+' : ''}${delta.toFixed(2)}%`) : undefined;

  return (
    <Paper
      elevation={0}
      sx={{
        bgcolor: 'rgba(22,27,34,0.85)',
        border: '1px solid #30363d',
        borderRadius: 2,
        p: 1.75,
      }}
    >
      <Typography sx={{ color: COLORS.sub, fontSize: 12 }}>{label}</Typography>
      <Typography sx={{ color: accent, fontSize: 22, fontWeight: 600, mt: 0.5 }}>{value}</Typography>
      {deltaText !== undefined && (
        <Typography sx={{ color: deltaColor, fontSize: 12, mt: 0.25 }}>{deltaText}</Typography>
      )}
    </Paper>
  );
}
