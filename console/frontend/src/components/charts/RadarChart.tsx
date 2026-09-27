import EChart from './EChart';
import { COLORS } from '../../theme';

interface RadarSeries {
  name: string;
  value: number[];
  color?: string;
}

interface Props {
  indicators: { name: string; max: number }[];
  series: RadarSeries[];
  height?: number;
}

/** 雷达图：用于百倍币多维度评分、链上 8 维、评分 7 维等。 */
export default function RadarChart({ indicators, series, height = 360 }: Props) {
  const option = {
    legend: {
      data: series.map((s) => s.name),
      textStyle: { color: COLORS.sub },
      top: 0,
    },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: COLORS.text, fontSize: 11 },
      splitLine: { lineStyle: { color: COLORS.border } },
      splitArea: { areaStyle: { color: ['rgba(88,166,255,0.04)', 'rgba(163,113,247,0.04)'] } },
      axisLine: { lineStyle: { color: COLORS.border } },
    },
    series: [
      {
        type: 'radar',
        data: series.map((s, i) => ({
          name: s.name,
          value: s.value,
          symbolSize: 4,
          lineStyle: { color: s.color || [COLORS.accent, COLORS.purple, COLORS.gold][i % 3], width: 2 },
          areaStyle: { color: (s.color || COLORS.accent) + '33' },
          itemStyle: { color: s.color || COLORS.accent },
        })),
      },
    ],
  };
  return <EChart option={option} height={height} />;
}
