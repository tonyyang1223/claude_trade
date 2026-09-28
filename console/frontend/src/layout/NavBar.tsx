import { NavLink } from 'react-router-dom';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';
import { AUTO_SELECTION, useAppStore } from '../store/useAppStore';
import { COLORS } from '../theme';

const TABS = [
  { to: '/market', label: '市场总览' },
  { to: '/radar', label: '百倍币雷达' },
  { to: '/token/bitcoin', label: '币种档案' },
  { to: '/compare', label: '竞品对比' },
  { to: '/onchain', label: '链上分析' },
  { to: '/scores', label: '评分与建议' },
  { to: '/history', label: '历史检索' },
  { to: '/health', label: '采集健康' },
];

/** 顶部导航：Logo + 8 个 Tab + 全局数据日期选择器（日历由 H1 驱动）。 */export default function NavBar() {
  const { selection, setSelection, dates, latest, latestComplete, latestMacro, calendarSource } =
    useAppStore();

  const hasFallback = !!latest && !!latestComplete && latest !== latestComplete;

  return (
    <AppBar position="sticky" color="default" sx={{ bgcolor: COLORS.panel, borderBottom: `1px solid ${COLORS.border}` }}>
      <Toolbar sx={{ gap: 2, flexWrap: 'wrap', py: 0.5 }}>
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

        <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 1.5 }}>
          {calendarSource === 'meta' && (
            <Tooltip title="历史库不可用，日期列表已降级自 /api/meta（无残缺日标记）">
              <Chip
                size="small"
                label="日历降级"
                sx={{ bgcolor: 'rgba(226,178,3,0.15)', color: COLORS.gold, fontSize: 11 }}
              />
            </Tooltip>
          )}
          {latestMacro && (
            <Tooltip title={`最新宏观快照日：${latestMacro}`}>
              <Chip
                size="small"
                label={`宏观 ${latestMacro}`}
                sx={{ bgcolor: 'rgba(163,113,247,0.15)', color: COLORS.purple, fontSize: 11 }}
              />
            </Tooltip>
          )}
          {hasFallback && (
            <Tooltip title={`最新扫描日 ${latest} 为残缺日，默认已回退至最后完整日 ${latestComplete}`}>
              <Chip
                size="small"
                label={`回退 → ${latestComplete}`}
                sx={{ bgcolor: 'rgba(226,178,3,0.15)', color: COLORS.gold, fontSize: 11 }}
              />
            </Tooltip>
          )}

          <FormControl size="small" sx={{ minWidth: 210 }}>
            <InputLabel sx={{ color: COLORS.sub }}>数据日期</InputLabel>
            <Select
              label="数据日期"
              value={selection}
              onChange={(e) => setSelection(e.target.value)}
              sx={{ color: COLORS.text, '.MuiOutlinedInput-notchedOutline': { borderColor: COLORS.border } }}
            >
              <MenuItem value={AUTO_SELECTION}>
                最后完整日（自动{latestComplete ? ` · ${latestComplete}` : ''}）
              </MenuItem>
              <MenuItem value="latest">
                最新扫描日{latest ? `（${latest}${latest !== latestComplete ? ' · 残缺' : ''}）` : ''}
              </MenuItem>
              {dates.map((d) => (
                <MenuItem key={d.date} value={d.date}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    <span>{d.date}</span>
                    {d.is_partial === true && (
                      <span style={{ color: COLORS.gold, fontSize: 11 }}>残缺</span>
                    )}
                    {d.is_partial !== true && d.deep_count > 0 && (
                      <span style={{ color: COLORS.sub, fontSize: 11 }}>deep {d.deep_count}</span>
                    )}
                  </Box>
                </MenuItem>
              ))}
              {dates.length === 0 && (
                <MenuItem value={AUTO_SELECTION} disabled>
                  暂无可用日期
                </MenuItem>
              )}
            </Select>
          </FormControl>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
