import type { CSSProperties } from 'react';
import ReactECharts from 'echarts-for-react';
import { COLORS, ECHARTS_DARK } from '../../theme';

interface Props {
  option: Record<string, any>;
  height?: number | string;
  style?: CSSProperties;
  onEvents?: Record<string, (params: any) => void>;
}

/**
 * ECharts 封装：统一注入暗色 token（背景透明、主文字色、tooltip 暗色样式）。
 * 所有图表均经此组件渲染，保证视觉语言一致。
 */
export default function EChart({ option, height = 320, style, onEvents }: Props) {
  const baseTooltip = {
    backgroundColor: ECHARTS_DARK.tooltip.backgroundColor,
    borderColor: ECHARTS_DARK.tooltip.borderColor,
    textStyle: { color: ECHARTS_DARK.tooltip.textStyle.color },
  };

  const merged = {
    backgroundColor: ECHARTS_DARK.backgroundColor,
    textStyle: { color: COLORS.text },
    tooltip: option.tooltip ? { ...baseTooltip, ...option.tooltip } : baseTooltip,
    ...option,
  };

  return (
    <ReactECharts
      option={merged}
      notMerge={false}
      lazyUpdate
      style={{ height, width: '100%', ...style }}
      onEvents={onEvents}
    />
  );
}
