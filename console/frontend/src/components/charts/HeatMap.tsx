import EChart from './EChart';
import { COLORS } from '../../theme';

interface Props {
  xCategories: string[];
  yCategories: string[];
  /** [xIndex, yIndex, value] */
  data: [number, number, number][];
  min?: number;
  max?: number;
  height?: number;
  fmt?: (v: number) => string;
}

/** 热力图：板块平均涨跌、维度强度矩阵等。视觉用绿→灰→红映射（红涨绿跌）。 */
export default function HeatMap({ xCategories, yCategories, data, min = -10, max = 10, height = 280, fmt }: Props) {
  const option: Record<string, any> = {
    tooltip: {
      position: 'top',
      formatter: (p: any) => {
        const v = p.data[2];
        return `${yCategories[p.data[1]]} · ${xCategories[p.data[0]]}<br/>${
          fmt ? fmt(v) : v
        }`;
      },
    },
    grid: { left: 80, right: 20, top: 20, bottom: 60 },
    xAxis: {
      type: 'category',
      data: xCategories,
      splitArea: { show: true },
      axisLabel: { color: COLORS.sub, rotate: 30, fontSize: 11 },
      axisLine: { lineStyle: { color: COLORS.border } },
    },
    yAxis: {
      type: 'category',
      data: yCategories,
      axisLabel: { color: COLORS.sub, fontSize: 11 },
      axisLine: { lineStyle: { color: COLORS.border } },
    },
    visualMap: {
      min,
      max,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: COLORS.sub },
      inRange: { color: [COLORS.down, COLORS.border, COLORS.up] },
    },
    series: [
      {
        name: 'value',
        type: 'heatmap',
        data,
        label: { show: true, color: COLORS.text, fontSize: 10, formatter: (p: any) => (fmt ? fmt(p.data[2]) : p.data[2]) },
        emphasis: { itemStyle: { borderColor: COLORS.accent, borderWidth: 1 } },
      },
    ],
  };
  return <EChart option={option} height={height} />;
}
