import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import { getScore, ApiError } from '../api/client';
import type { Score } from '../types/models';
import { COLORS } from '../theme';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import RadarChart from '../components/charts/RadarChart';
import Loading from '../components/common/Loading';
import EmptyState from '../components/common/EmptyState';

const DIM_LABELS: Record<string, string> = {
  market: '市场',
  technical: '技术',
  onchain: '链上',
  sentiment: '情绪',
  github: 'GitHub',
  social: '社交',
  risk: '风险',
};

export default function ScoresAdvice() {
  const { id } = useParams();
  const [coinId, setCoinId] = useState(id || 'bitcoin');
  const [data, setData] = useState<Score | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      setCoinId(id);
      load(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const load = (cid: string) => {
    if (!cid.trim()) {
      setError('请输入币种 ID');
      return;
    }
    setLoading(true);
    setError(null);
    getScore(cid.trim())
      .then((d) => setData(d))
      .catch((e: ApiError) => setError(e.message || '评分获取失败（可能为网络受限）'))
      .finally(() => setLoading(false));
  };

  const scores = data?.scores || {};
  const indicators = Object.keys(scores).map((k) => ({ name: DIM_LABELS[k] || k, max: 5 }));
  const series = data ? [{ name: data.symbol || data.coinId, value: Object.values(scores), color: COLORS.purple }] : [];
  const advice = data?.advice || {};

  return (
    <div>
      <PageHeader title="评分与建议" subtitle="复用 src.analysis.scorer + advice（可能触网）" />

      <Card sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
          <TextField
            value={coinId}
            onChange={(e) => setCoinId(e.target.value)}
            size="small"
            placeholder="CoinGecko 币种 ID，如 bitcoin"
            sx={{ flex: 1, minWidth: 260, input: { color: COLORS.text } }}
          />
          <Button variant="contained" onClick={() => load(coinId)} disabled={loading} sx={{ bgcolor: COLORS.accent, color: '#0d1117' }}>
            {loading ? <CircularProgress size={18} sx={{ color: '#0d1117' }} /> : '获取评分'}
          </Button>
        </Box>
        {error && <Box sx={{ mt: 1, color: COLORS.up, fontSize: 13 }}>{error}</Box>}
      </Card>

      {loading && <Loading label="正在计算多维评分…" />}

      {!loading && data && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Card title={`多维评分雷达 (${data.symbol || data.coinId})`} subtitle={`综合分 ${data.totalScore.toFixed(1)} / 100 · 评级 ${data.rating || '-'}`}>
              {indicators.length ? (
                <RadarChart indicators={indicators} series={series} height={360} />
              ) : (
                <EmptyState message="无评分数据" hint={error || undefined} />
              )}
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card title="综合建议">
              <Box sx={{ display: 'flex', gap: 1, mb: 1.5, flexWrap: 'wrap' }}>
                <Chip label={`评级: ${data.rating || '-'}`} sx={{ bgcolor: 'rgba(163,113,247,0.15)', color: COLORS.purple }} />
                <Chip label={`风险: ${data.riskLevel || '-'}`} sx={{ bgcolor: 'rgba(246,70,93,0.15)', color: COLORS.up }} />
                <Chip label={`建议仓位: ${advice.positionRange || '-'}`} sx={{ bgcolor: 'rgba(226,178,3,0.15)', color: COLORS.gold }} />
              </Box>
              <Typography sx={{ color: COLORS.text, fontSize: 13, mb: 1 }}>
                <b>倾向：</b>{advice.action || data.recommendation || '-'}
              </Typography>
              {advice.horizon && (
                <Typography sx={{ color: COLORS.text, fontSize: 13, mb: 1 }}>
                  <b>周期：</b>{advice.horizon}
                </Typography>
              )}
              <Typography sx={{ color: COLORS.sub, fontSize: 12, mb: 0.5 }}>触发条件</Typography>
              <Box sx={{ pl: 2 }}>
                {(advice.triggers || []).map((t: string, i: number) => (
                  <li key={i} style={{ color: COLORS.text, fontSize: 13, marginBottom: 4 }}>{t}</li>
                ))}
                {!advice.triggers?.length && <Typography sx={{ color: COLORS.sub, fontSize: 13 }}>无</Typography>}
              </Box>
            </Card>

            <Card title="免责声明" sx={{ mt: 2 }}>
              <Typography sx={{ color: COLORS.sub, fontSize: 12, lineHeight: 1.6 }}>
                {advice.disclaimer || '以上为量化模型研究参考，不构成投资建议。'}
              </Typography>
            </Card>
          </Grid>
        </Grid>
      )}

      {!loading && !data && !error && (
        <EmptyState message="输入币种 ID 后点击「获取评分」" />
      )}
    </div>
  );
}
