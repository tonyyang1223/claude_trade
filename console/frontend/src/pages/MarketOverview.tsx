import { useEffect, useState } from 'react';
import Grid from '@mui/material/Grid';
import { useAppStore } from '../store/useAppStore';
import { getMarketOverview, getMeta, ApiError } from '../api/client';
import type { MarketOverview as MO, MetaInfo } from '../types/models';
import { COLORS } from '../theme';
import { fmtMcap, fmtPct, fmtNum, colorForChange } from '../utils/format';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import KpiCard from '../components/charts/KpiCard';
import BarChart from '../components/charts/BarChart';
import HeatMap from '../components/charts/HeatMap';
import Loading from '../components/common/Loading';
import EmptyState from '../components/common/EmptyState';

export default function MarketOverview() {
  const { date } = useAppStore();
  const [data, setData] = useState<MO | null>(null);
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([getMarketOverview(date), getMeta().catch(() => null)])
      .then(([ov, m]) => {
        setData(ov);
        setMeta(m);
      })
      .catch((e: ApiError) => setError(e.message || '加载失败'))
      .finally(() => setLoading(false));
  }, [date]);

  if (loading) return <Loading label="加载市场总览…" />;
  if (error) return <EmptyState message="市场总览加载失败" hint={error} />;
  if (!data) return <EmptyState message="暂无市场数据" />;

  const k = data.kpi;
  const distItems = (data.distribution?.labels || []).map((lab, i) => ({
    category: lab,
    value: data.distribution.values[i],
    color: lab.startsWith('+') ? COLORS.up : lab.startsWith('-') ? COLORS.down : COLORS.sub,
  }));

  const gainerItems = data.gainers.map((c) => ({
    category: c.sym || c.id,
    value: c.chg24 || 0,
    color: COLORS.up,
  }));
  const loserItems = data.losers.map((c) => ({
    category: c.sym || c.id,
    value: c.chg24 || 0,
    color: COLORS.down,
  }));
  const mcapItems = data.topByMcap.map((c) => ({
    category: c.sym || c.id,
    value: c.mcap || 0,
    color: COLORS.accent,
  }));

  const sectorX = data.sectors.map((s) => s.cat);
  const sectorHeat: [number, number, number][] = data.sectors.map((s, i) => [i, 0, s.avgChg]);

  return (
    <div>
      <PageHeader
        title="市场总览"
        subtitle={`数据日期 ${data.meta?.date || meta?.date || '-'} · 扫描时间 ${data.meta?.scanTime || '-'}`}
      />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} md={2}>
          <KpiCard label="总市值" value={fmtMcap(k.totalMcap)} />
        </Grid>
        <Grid item xs={6} md={2}>
          <KpiCard label="监控币种" value={fmtNum(k.coinCnt)} />
        </Grid>
        <Grid item xs={6} md={2}>
          <KpiCard label="平均 24h 涨跌" value={fmtPct(k.avgChg)} delta={k.avgChg} deltaFormatter={fmtPct} />
        </Grid>
        <Grid item xs={6} md={2}>
          <KpiCard
            label="上涨 / 下跌"
            value={
              <span>
                <span style={{ color: COLORS.up }}>{fmtNum(k.upCnt)}</span> /{' '}
                <span style={{ color: COLORS.down }}>{fmtNum(k.downCnt)}</span>
              </span>
            }
          />
        </Grid>
        <Grid item xs={6} md={2}>
          <KpiCard label="深度研究" value={fmtNum(k.deepTotal)} />
        </Grid>
        <Grid item xs={6} md={2}>
          <KpiCard
            label="BTC 占比"
            value={k.btcDominance != null ? `${k.btcDominance.toFixed(1)}%` : '—'}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card title="24h 涨跌分布" subtitle={`全部 ${fmtNum(k.coinCnt)} 币`}>
            <BarChart items={distItems} height={300} valueFormatter={(v) => `${v} 币`} />
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card title="板块平均 24h 涨跌" subtitle="红涨绿跌（热力）">
            {sectorX.length ? (
              <HeatMap xCategories={sectorX} yCategories={['24h涨跌']} data={sectorHeat} min={-15} max={15} fmt={fmtPct} />
            ) : (
              <EmptyState message="暂无板块数据" />
            )}
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card title="24h 涨幅榜 TOP15" subtitle="市值排名前 300">
            {gainerItems.length ? <BarChart items={gainerItems} horizontal height={360} valueFormatter={fmtPct} /> : <EmptyState message="暂无数据" />}
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card title="24h 跌幅榜 TOP15" subtitle="市值排名前 300">
            {loserItems.length ? <BarChart items={loserItems} horizontal height={360} valueFormatter={fmtPct} /> : <EmptyState message="暂无数据" />}
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card title="市值 TOP15">
            {mcapItems.length ? <BarChart items={mcapItems} horizontal height={360} valueFormatter={fmtMcap} /> : <EmptyState message="暂无数据" />}
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card title="板块概览" subtitle="点击板块名查看代表币（在百倍币雷达中可按板块筛选）">
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ color: COLORS.sub, textAlign: 'right' }}>
                    <th style={{ textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid #30363d' }}>板块</th>
                    <th style={{ padding: '8px 10px', borderBottom: '1px solid #30363d' }}>币种数</th>
                    <th style={{ padding: '8px 10px', borderBottom: '1px solid #30363d' }}>总市值</th>
                    <th style={{ padding: '8px 10px', borderBottom: '1px solid #30363d' }}>平均 24h</th>
                  </tr>
                </thead>
                <tbody>
                  {data.sectors.map((s) => (
                    <tr key={s.cat}>
                      <td style={{ textAlign: 'left', padding: '7px 10px', color: COLORS.text }}>{s.cat}</td>
                      <td style={{ textAlign: 'right', padding: '7px 10px' }}>{fmtNum(s.count)}</td>
                      <td style={{ textAlign: 'right', padding: '7px 10px' }}>{fmtMcap(s.mcap)}</td>
                      <td style={{ textAlign: 'right', padding: '7px 10px', color: colorForChange(s.avgChg) }}>{fmtPct(s.avgChg)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </Grid>
      </Grid>
    </div>
  );
}
