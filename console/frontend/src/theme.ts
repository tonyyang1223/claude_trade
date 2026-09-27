import { createTheme } from '@mui/material/styles';

/**
 * 视觉 token 集中定义 —— 与 build_dashboard 看板一致的深色科技风。
 * 国内惯例：涨红跌绿。
 */
export const COLORS = {
  bg: '#0d1117',
  panel: '#161b22',
  border: '#30363d',
  text: '#e6edf3',
  sub: '#8b949e',
  up: '#f6465d', // 涨（红）
  down: '#2ebd85', // 跌（绿）
  accent: '#58a6ff', // 主蓝
  gold: '#e2b203',
  purple: '#a371f7',
  // 主色渐变（图表用）
  blue: '#3b82f6',
  cyan: '#22d3ee',
  violet: '#8b5cf6',
};

/** ECharts 暗色 token（注入到每个图表 option）。 */
export const ECHARTS_DARK = {
  backgroundColor: 'transparent',
  textStyle: {
    color: COLORS.text,
    colorSub: COLORS.sub,
  },
  up: COLORS.up,
  down: COLORS.down,
  axisColor: COLORS.border,
  splitColor: '#21262d',
  tooltip: {
    backgroundColor: COLORS.panel,
    borderColor: COLORS.border,
    textStyle: { color: COLORS.text },
  },
};

/** MUI 深色主题。 */
export const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: COLORS.bg,
      paper: COLORS.panel,
    },
    primary: { main: COLORS.accent },
    secondary: { main: COLORS.purple },
    error: { main: COLORS.up },
    success: { main: COLORS.down },
    text: {
      primary: COLORS.text,
      secondary: COLORS.sub,
    },
    divider: COLORS.border,
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Segoe UI","Microsoft YaHei",system-ui,sans-serif',
    fontSize: 13,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: COLORS.panel,
          border: `1px solid ${COLORS.border}`,
        },
      },
    },
  },
});

export default theme;
