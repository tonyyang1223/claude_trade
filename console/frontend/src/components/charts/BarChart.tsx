import EChart from './EChart';
import { COLORS } from '../../theme';

interface BarItem {
  category: string;
  value: number;
  color?: string;
}

interface Props {
  items: BarItem[];
  height?: number;
  horizontal?: boolean;
  valueFormatter?: (v: number) => string;
  yName?: string;
}

/** 柱状图：支持横向/纵向，颜色可逐条覆盖（用于涨跌榜、评分对比等）。 */
export default function BarChart({
  items,
  height = 320,
  horizontal = false,
  valueFormatter,
  yName,
}: Props) {
  const categories = items.map((i) => i.category);
  const values = items.map((i) => ({
    value: i.value,
    itemStyle: { color: i.color || COLORS.accent, borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] },
  }));

  const axisCommon = {
    axisLine: { lineStyle: { color: COLORS.border } },
    axisLabel: { color: COLORS.sub, fontSize: 11 },
    splitLine: { lineStyle: { color: COLORS.split } },
  };

  const option: Record<string, any> = {
    grid: horizontal
      ? { left: 90, right: 60, top: 16, bottom: 24 }
      : { left: 50, right: 20, top: 24, bottom: 70 },
    tooltip: {
      trigger: 'item',
      valueFormatter: valueFormatter ? (v: number) => valueFormatter(v) : undefined,
    },
    xAxis: horizontal
      ? { type: 'value', name: yName, ...axisCommon }
      : { type: 'category', data: categories, ...axisCommon, axisLabel: { ...axisCommon.axisLabel, rotate: categories.length > 6 ? 30 : 0 } },
    yAxis: horizontal
      ? { type: 'category', data: categories, ...axisCommon }
      : { type: 'value', name: yName, ...axisCommon },
    series: [{ type: 'bar', data: values, barWidth: '55%' }],
  };
  return <EChart option={option} height={height} />;
}
