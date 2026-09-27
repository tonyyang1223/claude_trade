import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import { useAppStore } from '../store/useAppStore';
import { getOpportunityRadar, ApiError } from '../api/client';
import type { OpportunityRadar, OpportunityItem } from '../types/models';
import { COLORS } from '../theme';
import { fmtMcap, fmtNum } from '../utils/format';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import RadarChart from '../components/charts/RadarChart';
import Loading from '../components/common/Loading';
import EmptyState from '../components/common/EmptyState';

const SORTS = ['composite', 'growth', 'community', 'mcapScale', 'narrative'];
const DIM_LABELS: Record<string, string> = {
  mcapScale: '市值规模',
  growth: '成长性',
  narrative: '叙事热度',
  community: '社区强度',
  onchain: '链上健康',
};

export default function HundredXRadar() {
  const { date } = useAppStore();
  const navigate = useNavigate();
  const [mcapMax, setMcapMax] = useState<string>('');
  const [sort, setSort] = useState('composite');
  const [data, setData] = useState<OpportunityRadar | null>(null);
  const [selected, setSelected] = useState<OpportunityItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    const mm = mcapMax ? Number(mcapMax) : undefined;
    getOpportunityRadar(date, mm, sort)
      .then((r) => {
        setData(r);
        setSelected(r.rankings[0] || null);
      })
      .catch((e: ApiError) => setError(e.message || '加载失败'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, sort]);

  const indicators = selected
    ? Object.keys(selected.dims).map((k) => ({ name: DIM_LABELS[k] || k, max: 100 }))
    : [];
  const series = selected
    ? [{ name: selected.sym || selected.id, value: Object.values(selected.dims), color: COLORS.accent }]
    : [];

  return (
    <div>
      <PageHeader
        title="百倍币机会雷达"
        subtitle="启发式多维打分（市值规模/成长性/叙事/社区/链上）—— 纯本地、零网络"
        actions={
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              value={mcapMax}
              onChange={(e) => setMcapMax(e.target.value)}
              size="small"
              placeholder="市值上限 USD"
              sx={{ width: 150, input: { color: COLORS.text } }}
            />
            <FormControl size="small" sx={{ minWidth: 130 }}>
              <InputLabel sx={{ color: COLORS.sub }}>排序</InputLabel>
              <Select
                label="排序"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                sx={{ color: COLORS.text, '.MuiOutlinedInput-notchedOutline': { borderColor: COLORS.border } }}
              >
                {SORTS.map((s) => (
                  <MenuItem key={s} value={s}>{s}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="outlined" size="small" onClick={load} sx={{ borderColor: COLORS.border, color: COLORS.text }}>
              刷新
            </Button>
          </Box>
        }
      />

      {error && <Box sx={{ mb: 2, color: COLORS.up, fontSize: 13 }}>{error}</Box>}
      {loading && <Loading label="计算机会雷达…" />}

      {!loading && data && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={5}>
            <Card title="维度雷达" subtitle={selected ? `${selected.name || selected.id} · 综合 ${selected.composite}` : ''}>
              {indicators.length ? <RadarChart indicators={indicators} series={series} height={380} /> : <EmptyState message="无维度数据" />}
            </Card>
          </Grid>
          <Grid item xs={12} md={7}>
            <Card title={`机会排行榜 (${data.meta.count ?? data.rankings.length})`} subtitle="点击行查看雷达">
              <Box sx={{ maxHeight: 520, overflow: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ color: COLORS.sub, textAlign: 'right', position: 'sticky', top: 0, background: '#161b22' }}>
                      <th style={{ textAlign: 'left', padding: '8px 8px', borderBottom: '1px solid #30363d' }}>#</th>
                      <th style={{ textAlign: 'left', padding: '8px 8px', borderBottom: '1px solid #30363d' }}>币种</th>
                      <th style={{ padding: '8px 8px', borderBottom: '1px solid #30363d' }}>综合</th>
                      <th style={{ padding: '8px 8px', borderBottom: '1px solid #30363d' }}>市值</th>
                      <th style={{ padding: '8px 8px', borderBottom: '1px solid #30363d' }}>板块</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.rankings.map((it, i) => (
                      <tr
                        key={it.id}
                        onClick={() => setSelected(it)}
                        style={{ cursor: 'pointer', background: selected?.id === it.id ? 'rgba(88,166,255,0.12)' : 'transparent' }}
                      >
                        <td style={{ textAlign: 'left', padding: '7px 8px', color: COLORS.sub }}>{i + 1}</td>
                        <td style={{ textAlign: 'left', padding: '7px 8px' }}>
                          <a
                            onClick={(e) => { e.stopPropagation(); navigate(`/token/${it.id}`); }}
                            style={{ color: COLORS.accent, textDecoration: 'none', cursor: 'pointer' }}
                          >
                            {it.sym || it.id}
                          </a>{' '}
                          <span style={{ color: COLORS.sub }}>{it.name}</span>
                        </td>
                        <td style={{ textAlign: 'right', padding: '7px 8px', color: COLORS.text, fontWeight: 600 }}>{it.composite.toFixed(1)}</td>
                        <td style={{ textAlign: 'right', padding: '7px 8px' }}>{fmtMcap(it.mcap)}</td>
                        <td style={{ textAlign: 'right', padding: '7px 8px', color: COLORS.sub }}>{it.category || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Box>
            </Card>
          </Grid>
        </Grid>
      )}

      {!loading && !data && (
        <EmptyState message="暂无机会数据" hint="尝试调整市值上限或排序方式" />
      )}
    </div>
  );
}
