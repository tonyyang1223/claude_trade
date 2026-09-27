/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 与 build_dashboard 看板一致的深色科技风色板
        bg: '#0d1117',
        panel: '#161b22',
        border: '#30363d',
        txt: '#e6edf3',
        sub: '#8b949e',
        up: '#f6465d', // 涨（红，国内惯例）
        down: '#2ebd85', // 跌（绿，国内惯例）
        accent: '#58a6ff', // 主蓝
        gold: '#e2b203',
        purple: '#a371f7',
      },
      backgroundImage: {
        'glass-grad': 'linear-gradient(145deg, rgba(31,111,235,0.10), rgba(163,113,247,0.06))',
      },
      boxShadow: {
        glass: '0 8px 24px rgba(0,0,0,0.35)',
      },
    },
  },
  plugins: [],
};
