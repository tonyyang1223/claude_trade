import EChart from './EChart';
import { COLORS } from '../../theme';

export interface LineSeries {
  name: string;
  /** null 表示该日缺失 —— 配合 connectNulls:false 断开，**绝不插值/补 0** */
  data: (number | null)[];
  color?: string;
  yAxisIndex?: number;
  area?: boolean;
  lineType?: 'solid' | 'dashed';
}

export interface LineYAxis {
  name?: string;
  inverse?: boolean;
  min?: number | 'dataMin';
  max?: number | 'dataMax';
  formatter?: (v: number) => string;
}

interface Props {
  xData: string[];
  series: LineSeries[];
  yAxes?: LineYAxis[];
  height?: number;
  /** 打开底部缩放条（日期跨度大时建议开） */
  zoom?: boolean;
  /** 用散点标出缺失日（配合 gaps 使用，提示「是缺，不是 0」） */
  gapDates?: string[];
}

const PALETTE = [COLORS.accent, COLORS.gold, COLORS.purple, COLORS.cyan, COLORS.blue, COLORS.down];

/**
 * 折线图：支持多 Y 轴、面积、缩放与**显式缺口**。
 *
 * 关键约定（对齐 ARCHITECTURE.md §8 H2）：`present=false` 的日期在数据中为 `null`，
 * `connectNulls:false` 让曲线断开，使「缺数据」与「数值为 0」在视觉上可区分。
 */
export default function LineChart({
  xData,
  series,
  yAxes,
  height = 320,
  zoom = false,
  gapDates,
}: Props) {
  const axisCommon = {
    axisLine: { lineStyle: { color: COLORS.border } },
    axisLabel: { color: COLORS.sub, fontSize: 11 },
    splitLine: { lineStyle: { color: COLORS.split } },
  };

  const yAxisList = (yAxes && yAxes.length ? yAxes : [{}]).map((y, i) => ({
    type: 'value' as const,
    name: y.name,
    inverse: y.inverse,
    min: y.min,
    max: y.max,
    position: i === 1 ? ('right' as const) : undefined,
    nameTextStyle: { color: COLORS.sub, fontSize: 11 },
    ...axisCommon,
    axisLabel: {
      ...axisCommon.axisLabel,
      formatter: y.formatter ? (v: number) => y.formatter!(v) : undefined,
    },
    splitLine: i === 0 ? axisCommon.splitLine : { show: false },
  }));

  const markPoints = (gapDates || []).map((d) => ({
    name: '缺数据',
    coord: [d, 0],
    value: '',
    symbolSize: 0,
    itemStyle: { color: 'transparent' },
    label: { show: false },
  }));

  const option: Record<string, any> = {
    grid: {
      left: 58,
      right: yAxisList.length > 1 ? 62 : 24,
      top: 34,
      bottom: zoom ? 56 : 34,
    },
    legend: {
      top: 0,
      textStyle: { color: COLORS.sub, fontSize: 11 },
      itemWidth: 14,
      itemHeight: 8,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', label: { backgroundColor: COLORS.panel } },
      // 缺失日在 tooltip 中显式标注，避免用户误读为 0
      formatter: (ps: any[]) => {
        const head = ps[0]?.axisValue ?? '';
        const lines = ps.map((p: any) => {
          const v = p.data;
          const txt = v === null || v === undefined ? '<span style="opacity:.6">缺数据</span>' : p.data;
          return `${p.marker}${p.seriesName}：${txt}`;
        });
        return [head, ...lines].join('<br/>');
      },
    },
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: false,
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, hideOverlap: true },
    },
    yAxis: yAxisList,
    dataZoom: zoom
      ? [
          { type: 'inside', start: 0, end: 100 },
          {
            type: 'slider',
            height: 18,
            bottom: 12,
            start: 0,
            end: 100,
            borderColor: COLORS.border,
            fillerColor: 'rgba(88,166,255,0.15)',
            handleStyle: { color: COLORS.accent },
            textStyle: { color: COLORS.sub, fontSize: 10 },
          },
        ]
      : undefined,
    series: series.map((s, i) => ({
      name: s.name,
      type: 'line',
      yAxisIndex: s.yAxisIndex || 0,
      data: s.data,
      // 核心：缺口断开，不做任何插值
      connectNulls: false,
      smooth: false,
      symbol: 'circle',
      symbolSize: 5,
      showSymbol: xData.length <= 60,
      lineStyle: { width: 2, type: s.lineType || 'solid', color: s.color || PALETTE[i % PALETTE.length] },
      itemStyle: { color: s.color || PALETTE[i % PALETTE.length] },
      areaStyle: s.area ? { opacity: 0.12 } : undefined,
      emphasis: { focus: 'series' },
      markPoint: i === 0 && markPoints.length ? { silent: true, data: markPoints } : undefined,
    })),
  };

  return <EChart option={option} height={height} />;
}
