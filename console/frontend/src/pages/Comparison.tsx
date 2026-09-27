import { useState } from 'react';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import { useAppStore } from '../store/useAppStore';
import { postComparison, ApiError } from '../api/client';
import type { Comparison } from '../types/models';
import { COLORS } from '../theme';
import { fmtNum } from '../utils/format';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import BarChart from '../components/charts/BarChart';
import Loading from '../components/common/Loading';
import EmptyState from '../components/common/EmptyState';

const QUICK = ['bitcoin', 'ethereum', 'solana', 'binancecoin', 'ripple', 'cardano'];

export default function Comparison() {
  const [ids, setIds] = useState('bitcoin,ethereum,solana');
  const [result, setResult] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = (raw: string) => {
    const list = raw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (list.length < 2) {
      setError('请至少输入 2 个币种 ID（以英文逗号分隔）');
      return;
    }
    setLoading(true);
    setError(null);
    postComparison(list)
      .then((r) => setResult(r))
      .catch((e: ApiError) => setError(e.message || '对比失败（可能为网络受限）'))
      .finally(() => setLoading(false));
  };

  const barItems = (result?.projects || []).map((p, i) => ({
    category: p.symbol || p.coin_id,
    value: p.total_score || 0,
    color: [COLORS.accent, COLORS.purple, COLORS.gold, COLORS.cyan, COLORS.blue][i % 5],
  }));

  const metrics = ['market_score', 'technical_score', 'onchain_score', 'sentiment_score', 'github_score', 'social_score', 'risk_score'];

  return (
    <div>
      <PageHeader title="竞品对比" subtitle="基于 src.analysis.comparison 的多维评分对比（可能触网）" />

      <Card sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
          <TextField
            value={ids}
            onChange={(e) => setIds(e.target.value)}
            size="small"
            placeholder="bitcoin,ethereum,solana"
            sx={{ flex: 1, minWidth: 280, input: { color: COLORS.text } }}
            InputLabelProps={{ style: { color: COLORS.sub } }}
          />
          <Button
            variant="contained"
            onClick={() => run(ids)}
            disabled={loading}
            sx={{ bgcolor: COLORS.accent, color: COLORS.bg }}
          >
            {loading ? <CircularProgress size={18} sx={{ color: COLORS.bg }} /> : '开始对比'}
          </Button>
        </Box>
        <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {QUICK.map((q) => (
            <Chip
              key={q}
              label={q}
              size="small"
              onClick={() => setIds((prev) => (prev ? `${prev},${q}` : q))}
              sx={{ bgcolor: 'rgba(88,166,255,0.12)', color: COLORS.accent, cursor: 'pointer' }}
            />
          ))}
        </Box>
      </Card>

      {error && (
        <Box sx={{ mb: 2, p: 1, borderRadius: 1, bgcolor: 'rgba(246,70,93,0.12)', color: COLORS.up, fontSize: 13 }}>
          {error}
        </Box>
      )}

      {loading && <Loading label="正在对比：需逐币联网抓取 7 个维度，实测 2 币约 2–3 分钟，请勿关闭页面…" />}

      {!loading && result && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={5}>
            <Card title="综合评分对比">
              {barItems.length ? <BarChart items={barItems} height={Math.max(240, barItems.length * 50)} /> : <EmptyState message="无评分数据" />}
            </Card>
          </Grid>
          <Grid item xs={12} md={7}>
            <Card title="维度明细" subtitle={result.winner ? `领先: ${result.winner}` : undefined}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ color: COLORS.sub, textAlign: 'right' }}>
                      <th style={{ textAlign: 'left', padding: 8, borderBottom: `1px solid ${COLORS.border}` }}>维度</th>
                      {result.projects.map((p) => (
                        <th key={p.coin_id} style={{ padding: 8, borderBottom: `1px solid ${COLORS.border}` }}>{p.symbol || p.coin_id}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.map((m) => (
                      <tr key={m}>
                        <td style={{ textAlign: 'left', padding: '6px 8px', color: COLORS.sub }}>{m.replace('_score', '')}</td>
                        {result.projects.map((p) => (
                          <td key={p.coin_id} style={{ textAlign: 'right', padding: '6px 8px' }}>{String(p[m as keyof typeof p] ?? '-')}</td>
                        ))}
                      </tr>
                    ))}
                    <tr>
                      <td style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 700, color: COLORS.text }}>综合</td>
                      {result.projects.map((p) => (
                        <td key={p.coin_id} style={{ textAlign: 'right', padding: '6px 8px', fontWeight: 700, color: COLORS.accent }}>{p.total_score ?? '-'}</td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </Card>
          </Grid>
          <Grid item xs={12}>
            <Card title="分析结论">
              <Typography sx={{ color: COLORS.text, fontSize: 13, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                {result.summary || '暂无结论（网络受限或未取到数据）。'}
              </Typography>
            </Card>
          </Grid>
        </Grid>
      )}

      {!loading && !result && !error && <EmptyState message="请输入币种并点击「开始对比」" />}
    </div>
  );
}
