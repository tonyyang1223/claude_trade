import { useState } from 'react';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import CircularProgress from '@mui/material/CircularProgress';
import { getOnchain, ApiError } from '../api/client';
import type { Onchain } from '../types/models';
import { COLORS } from '../theme';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import RadarChart from '../components/charts/RadarChart';
import Loading from '../components/common/Loading';
import EmptyState from '../components/common/EmptyState';

const CHAINS = ['bnb', 'sol', 'robinhood'];
const DIM_LABELS: Record<string, string> = {
  security: '安全',
  trend: '趋势',
  momentum: '动量',
  liquidity_health: '流动性',
  sentiment: '情绪',
  innovation: '创新',
  taxonomy: '类别',
  community: '社区',
};

export default function Onchain() {
  const [chain, setChain] = useState('bnb');
  const [query, setQuery] = useState('');
  const [demo, setDemo] = useState(false);
  const [data, setData] = useState<Onchain | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = () => {
    if (!query.trim()) {
      setError('请输入代币符号或合约地址');
      return;
    }
    setLoading(true);
    setError(null);
    getOnchain(chain, query.trim(), demo)
      .then((d) => setData(d))
      .catch((e: ApiError) => setError(e.message || '链上分析失败'))
      .finally(() => setLoading(false));
  };

  const dims = data?.dims || {};
  const indicators = Object.keys(dims).map((k) => ({ name: DIM_LABELS[k] || k, max: 10 }));
  const series = data
    ? [{ name: data.symbol || data.address, value: Object.values(dims), color: COLORS.accent }]
    : [];

  return (
    <div>
      <PageHeader title="链上分析" subtitle="复用 src.chain 八维评分（可能触网；可开 Demo 离线样例）" />

      <Card sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel sx={{ color: COLORS.sub }}>链</InputLabel>
            <Select
              label="链"
              value={chain}
              onChange={(e) => setChain(e.target.value)}
              sx={{ color: COLORS.text, '.MuiOutlinedInput-notchedOutline': { borderColor: COLORS.border } }}
            >
              {CHAINS.map((c) => (
                <MenuItem key={c} value={c}>{c.toUpperCase()}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            size="small"
            placeholder="代币符号或合约地址，如 CAKE / 0x…"
            sx={{ flex: 1, minWidth: 260, input: { color: COLORS.text } }}
          />
          <FormControlLabel
            control={<Switch checked={demo} onChange={(e) => setDemo(e.target.checked)} />}
            label={<span style={{ color: COLORS.sub, fontSize: 13 }}>Demo 模式</span>}
          />
          <Button variant="contained" onClick={run} disabled={loading} sx={{ bgcolor: COLORS.accent, color: '#0d1117' }}>
            {loading ? <CircularProgress size={18} sx={{ color: '#0d1117' }} /> : '分析'}
          </Button>
        </Box>
        {error && (
          <Box sx={{ mt: 1, color: COLORS.up, fontSize: 13 }}>{error}</Box>
        )}
      </Card>

      {loading && <Loading label="正在进行链上多维分析…" />}

      {!loading && data && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Card title={`八维评分雷达 (${data.symbol || data.address})`} subtitle={`综合分 ${data.total.toFixed(1)} / 10`}>
              {indicators.length ? (
                <RadarChart indicators={indicators} series={series} height={380} />
              ) : (
                <EmptyState message="无维度数据" hint={data.disclaimer || undefined} />
              )}
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card title="决策建议">
              <Box sx={{ display: 'flex', gap: 1, mb: 1.5, flexWrap: 'wrap' }}>
                <Chip label={`决策: ${data.decision || '-'}`} sx={{ bgcolor: 'rgba(88,166,255,0.15)', color: COLORS.accent }} />
                <Chip label={`风险: ${data.risk || '-'}`} sx={{ bgcolor: 'rgba(246,70,93,0.15)', color: COLORS.up }} />
                <Chip label={`仓位: ${data.position || '-'}`} sx={{ bgcolor: 'rgba(226,178,3,0.15)', color: COLORS.gold }} />
              </Box>
              <Typography sx={{ color: COLORS.sub, fontSize: 12, mb: 0.5 }}>触发条件 / 护栏</Typography>
              <Box sx={{ pl: 2 }}>
                {(data.triggers || []).map((t, i) => (
                  <li key={i} style={{ color: COLORS.text, fontSize: 13, marginBottom: 4 }}>{t}</li>
                ))}
                {!data.triggers?.length && <Typography sx={{ color: COLORS.sub, fontSize: 13 }}>无</Typography>}
              </Box>
              <Typography sx={{ color: COLORS.sub, fontSize: 12, mt: 1, mb: 0.5 }}>缺失维度（已排除加权）</Typography>
              <Typography sx={{ color: COLORS.text, fontSize: 13 }}>{(data.missing || []).join('、') || '无'}</Typography>
            </Card>

            <Card title="红旗标记" sx={{ mt: 2 }}>
              {data.flags?.length ? (
                data.flags.map((f: any, i: number) => (
                  <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'center', py: 0.5 }}>
                    <Chip
                      label={f.level}
                      size="small"
                      sx={{
                        bgcolor: f.level === 'bad' ? 'rgba(246,70,93,0.2)' : f.level === 'warn' ? 'rgba(226,178,3,0.2)' : 'rgba(46,189,133,0.2)',
                        color: f.level === 'bad' ? COLORS.up : f.level === 'warn' ? COLORS.gold : COLORS.down,
                      }}
                    />
                    <Typography sx={{ color: COLORS.text, fontSize: 12 }}>{f.msg}</Typography>
                  </Box>
                ))
              ) : (
                <EmptyState message="无红旗" />
              )}
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card title="免责声明">
              <Typography sx={{ color: COLORS.sub, fontSize: 12, lineHeight: 1.6 }}>{data.disclaimer || '—'}</Typography>
            </Card>
          </Grid>
        </Grid>
      )}

      {!loading && !data && !error && (
        <EmptyState message="输入链与代币后点击「分析」" hint="无链上地址时可用 Demo 模式查看样例" />
      )}
    </div>
  );
}
