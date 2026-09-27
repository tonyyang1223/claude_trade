import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import { useAppStore } from '../store/useAppStore';
import { getMeta } from '../api/client';
import { COLORS } from '../theme';

const TABS = [
  { to: '/market', label: '市场总览' },
  { to: '/radar', label: '百倍币雷达' },
  { to: '/token/bitcoin', label: '币种档案' },
  { to: '/compare', label: '竞品对比' },
  { to: '/onchain', label: '链上分析' },
  { to: '/scores', label: '评分与建议' },
];

/** 顶部导航：Logo + 6 个 Tab + 全局数据日期选择器。 */
export default function NavBar() {
  const { date, setDate } = useAppStore();
  const [dates, setDates] = useState<string[]>([]);

  useEffect(() => {
    getMeta()
      .then((m) => setDates(m.availableDates || []))
      .catch(() => setDates([]));
  }, []);

  return (
    <AppBar position="sticky" color="default" sx={{ bgcolor: COLORS.panel, borderBottom: `1px solid ${COLORS.border}` }}>
      <Toolbar sx={{ gap: 2 }}>
        <Typography sx={{ fontWeight: 700, color: COLORS.accent, whiteSpace: 'nowrap' }}>
          claude_trading
        </Typography>
        <Typography sx={{ color: COLORS.sub, fontSize: 13, whiteSpace: 'nowrap' }}>投研控制台</Typography>

        <Box sx={{ display: 'flex', gap: 1, ml: 2, flexWrap: 'wrap' }}>
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              style={({ isActive }) => ({
                padding: '6px 14px',
                borderRadius: 8,
                textDecoration: 'none',
                fontSize: 14,
                color: isActive ? COLORS.accent : COLORS.sub,
                border: `1px solid ${isActive ? COLORS.accent : COLORS.border}`,
                background: isActive ? 'rgba(31,111,235,0.2)' : 'transparent',
                whiteSpace: 'nowrap',
              })}
            >
              {t.label}
            </NavLink>
          ))}
        </Box>

        <Box sx={{ ml: 'auto' }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel sx={{ color: COLORS.sub }}>数据日期</InputLabel>
            <Select
              label="数据日期"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              sx={{ color: COLORS.text, '.MuiOutlinedInput-notchedOutline': { borderColor: COLORS.border } }}
            >
              <MenuItem value="latest">最新 (latest)</MenuItem>
              {dates.map((d) => (
                <MenuItem key={d} value={d}>
                  {d}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
