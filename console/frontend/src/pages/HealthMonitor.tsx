import { useEffect, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Tooltip from '@mui/material/Tooltip';
import { getHealthOverview, getHealthSources, softMiss } from '../api/history';
import type { HealthOverview, HealthSources, SourceHealthDay } from '../types/history';
import { COLORS } from '../theme';
import { fmtNum } from '../utils/format';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import KpiCard from '../components/charts/KpiCard';
import Loading from '../components/common/Loading';
import EmptyState from '../components/common/EmptyState';
import HeatMap from '../components/charts/HeatMap';
import LineChart from '../components/charts/LineChart';

const STATUS_LABEL: Record<string, string> = {
  ok: '正常',
  stale: '停更',
  empty: '无数据',
  unknown: '未知',
};

const STATUS_COLOR: Record<string, string> = {
  ok: COLORS.down,
  stale: COLORS.gold,
  empty: COLORS.sub,
  unknown: COLORS.sub,
};

const COLLECTION_LABEL: Record<string, string> = {
  scan: '每日扫描（scan_day）',
  macro: '宏观快照（macro_snapshot）',
};

const ANOMALY_LABEL: Record<string, string> = {
  partial_day: '残缺日',
  stale_collection: '链路停更',
  scan_gap: '扫描断档',
};

/**
 * 采集健康度页（场景③ —— H6 + H7）。
 *
 * 回答「我的数据源还活着吗、什么时候开始不新鲜了」：
 * - **链路新鲜度**：scan / macro 的 last_date、gap_days、status（阈值 STALE_DAYS=2）；
 * - **异常清单**：残缺日、停更链路、扫描断档；
 * - **逐源健康度**：日期 × 来源的成功率热力图 + 平均置信度；
 * - **源集合漂移**：每日来源数量（13 vs 14 这类口径漂移探针）；
 * - **入库批次**：最近 10 个 batch 的 mode/status/rows_loaded/rows_rejected。
 */
export default function HealthMonitor() {
  const [ov, setOv] = useState<HealthOverview | null>(null);
  const [src, setSrc] = useState<HealthSources | null>(null);
  const [loading, setLoading] = useState(true);
  const [ovErr, setOvErr] = useState<string | null>(null);
  const [srcErr, setSrcErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getHealthOverview()
      .then((d) => alive && setOv(d))
      .catch((e: any) => {
        if (!alive) return;
        if (softMiss(e)) setOv((e.data as HealthOverview) || null);
        else setOvErr(e?.message || '采集健康度加载失败');
      })
      .finally(() => alive && setLoading(false));
    getHealthSources()
      .then((d) => alive && setSrc(d))
      .catch((e: any) => {
        if (!alive) return;
        if (softMiss(e)) setSrc((e.data as HealthSources) || null);
        else setSrcErr(e?.message || '逐源健康度加载失败');
      });
    return () => {
      alive = false;
    };
  }, []);

  const collections = useMemo(() => Object.entries(ov?.collections || {}), [ov]);

  // 逐源热力图：日期（列）× 来源（行），值为成功率
  const { heatX, heatY, heatData, confidenceByDate } = useMemo(() => {
    const rows: SourceHealthDay[] = src?.by_date || [];
    const dates = Array.from(new Set(rows.map((r) => r.date))).sort();
    const sources = Array.from(new Set(rows.map((r) => r.source))).sort();
    const dIdx = new Map(dates.map((d, i) => [d, i]));
    const sIdx = new Map(sources.map((s, i) => [s, i]));
    const data: [number, number, number][] = [];
    rows.forEach((r) => {
      if (r.success_rate === null || r.success_rate === undefined) return;
      const di = dIdx.get(r.date);
      const si = sIdx.get(r.source);
      if (di === undefined || si === undefined) return;
      data.push([di, si, r.success_rate]);
    });

    // 平均置信度：逐日对所有来源取均值（仅计有值的行）
    const confMap = new Map<string, { sum: number; n: number }>();
    rows.forEach((r) => {
      if (r.avg_confidence === null || r.avg_confidence === undefined) return;
      const cur = confMap.get(r.date) || { sum: 0, n: 0 };
      cur.sum += r.avg_confidence;
      cur.n += 1;
      confMap.set(r.date, cur);
    });
    const confSeries = dates.map((d) => {
      const c = confMap.get(d);
      return c && c.n ? c.sum / c.n : null;
    });

    return { heatX: dates, heatY: sources, heatData: data, confidenceByDate: confSeries };
  }, [src]);

  const driftX = (src?.drift || []).map((d) => d.date);
  const driftY = (src?.drift || []).map((d) => d.n_sources);
  const driftValues = Array.from(new Set(driftY)).sort((a, b) => a - b);
  const driftUnstable = driftValues.length > 1;

  if (loading && !ov) return <Loading label="加载采集健康度…" />;

  return (
    <div>
      <PageHeader
        title="采集健康度"
        subtitle="H7 链路新鲜度 / 异常 / 批次 · H6 逐源成功率 / 源漂移 · 阈值 STALE_DAYS=2"
      />

      {ovErr && <EmptyState message="采集健康度总览加载失败" hint={ovErr} />}

      {/* ---------------- 链路新鲜度 ---------------- */}
      {!ovErr && ov && (
        <Grid container spacing={2} sx={{ mb: 2 }}>
          {collections.length === 0 && (
            <Grid item xs={12}>
              <EmptyState message="历史库不可用" hint="H7 返回 503 + 空结构（后端约定：数据缺失绝不 500）。" />
            </Grid>
          )}
          {collections.map(([name, st]) => (
            <Grid item xs={12} sm={6} md={3} key={name}>
              <Card
                title={COLLECTION_LABEL[name] || name}
                actions={
                  <Chip
                    size="small"
                    label={STATUS_LABEL[st.status] || st.status}
                    sx={{
                      fontSize: 11,
                      bgcolor: `${STATUS_COLOR[st.status] || COLORS.sub}22`,
                      color: STATUS_COLOR[st.status] || COLORS.sub,
                    }}
                  />
                }
              >
                <Typography sx={{ color: COLORS.text, fontSize: 15, fontWeight: 600 }}>
                  {st.last_date || '—'}
                </Typography>
                <Typography sx={{ color: COLORS.sub, fontSize: 12, mt: 0.5 }}>
                  距参照日 {st.gap_days === null || st.gap_days === undefined ? '—' : `${st.gap_days} 天`}
                  {st.status === 'stale' ? ' · 已超过停更阈值' : ''}
                </Typography>
              </Card>
            </Grid>
          ))}
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard label="异常条数" value={fmtNum((ov?.anomalies || []).length)} accent={(ov?.anomalies || []).length ? COLORS.gold : COLORS.text} />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard label="扫描断档日" value={fmtNum((src?.gaps || []).length)} />
          </Grid>
        </Grid>
      )}

      {/* ---------------- 异常清单 ---------------- */}
      {!ovErr && (
        <Card title="异常清单" subtitle="残缺日 / 链路停更 / 扫描断档">
          {(ov?.anomalies || []).length === 0 ? (
            <EmptyState message="无异常" hint="所有链路新鲜度正常，且无残缺日与断档。" />
          ) : (
            <Box sx={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
                <thead>
                  <tr style={{ color: COLORS.sub, textAlign: 'left' }}>
                    <th style={{ padding: '7px 10px', borderBottom: `1px solid ${COLORS.border}` }}>类型</th>
                    <th style={{ padding: '7px 10px', borderBottom: `1px solid ${COLORS.border}` }}>对象</th>
                    <th style={{ padding: '7px 10px', borderBottom: `1px solid ${COLORS.border}` }}>详情</th>
                  </tr>
                </thead>
                <tbody>
                  {(ov?.anomalies || []).map((a, i) => (
                    <tr key={i}>
                      <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, color: COLORS.gold }}>
                        {ANOMALY_LABEL[a.kind] || a.kind}
                      </td>
                      <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, color: COLORS.text }}>
                        {a.date || a.collection || (Array.isArray(a.window) ? a.window.join(' → ') : '—')}
                      </td>
                      <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, color: COLORS.sub }}>
                        {a.detail ||
                          (a.kind === 'stale_collection'
                            ? `最后日期 ${a.last_date}，已 ${a.gap_days} 天未更新`
                            : a.kind === 'scan_gap'
                            ? `缺失 ${a.missing_days} 天`
                            : '—')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Box>
          )}
        </Card>
      )}

      {/* ---------------- 逐源成功率 ---------------- */}
      <Box sx={{ mt: 2 }}>
        <Card
          title="逐源成功率"
          subtitle={
            srcErr
              ? srcErr
              : `H6 · source_status · ${heatY.length} 个来源 × ${heatX.length} 个采集日 · 单元值 = 成功率(%)`
          }
        >
          {srcErr ? (
            <EmptyState message="逐源健康度加载失败" hint={srcErr} />
          ) : heatData.length ? (
            <HeatMap
              xCategories={heatX}
              yCategories={heatY}
              data={heatData}
              min={0}
              max={100}
              height={Math.max(320, heatY.length * 22 + 90)}
              fmt={(v) => `${v.toFixed(0)}%`}
            />
          ) : (
            <EmptyState
              message="所选区间无逐源健康度数据"
              hint="H6 返回 404 + 空结构（该区间 source_status 无行），并非加载失败。"
            />
          )}
        </Card>
      </Box>

      <Box sx={{ mt: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Card title="日均置信度" subtitle="逐日对各来源 avg_confidence 取均值（缺值断开）">
              {heatX.length ? (
                <LineChart
                  xData={heatX}
                  series={[{ name: '平均置信度', data: confidenceByDate, color: COLORS.accent, area: true }]}
                  yAxes={[{ min: 0, max: 1, formatter: (v) => v.toFixed(2) }]}
                  height={280}
                  zoom={heatX.length > 40}
                />
              ) : (
                <EmptyState message="暂无置信度数据" />
              )}
              <Typography sx={{ color: COLORS.sub, fontSize: 11, mt: 0.5 }}>
                口径提示：14 个来源中仅 6 个上报 confidence（funding_rate / open_interest / sentiment /
                stablecoin_flows / twitter 及部分 reddit），其余恒为 NULL 且**不被计入均值**——
                该曲线代表「有上报来源的平均置信度」，非全量来源。
              </Typography>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card
              title="来源集合规模（漂移探针）"
              subtitle={driftUnstable ? `存在口径漂移：规模取值 ${driftValues.join(' / ')}` : '各日来源数量一致'}
              actions={
                driftUnstable ? (
                  <Chip size="small" label="漂移" sx={{ fontSize: 11, bgcolor: 'rgba(226,178,3,0.15)', color: COLORS.gold }} />
                ) : null
              }
            >
              {driftX.length ? (
                <LineChart
                  xData={driftX}
                  series={[{ name: '来源数量', data: driftY, color: driftUnstable ? COLORS.gold : COLORS.down }]}
                  yAxes={[{ formatter: (v) => v.toFixed(0), min: Math.max(0, Math.min(...driftY) - 1) }]}
                  height={280}
                  zoom={driftX.length > 40}
                />
              ) : (
                <EmptyState message="暂无漂移数据" />
              )}
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* ---------------- 入库批次 ---------------- */}
      <Box sx={{ mt: 2 }}>
        <Card title="入库批次" subtitle="最近 10 个 batch（ingest_batch）· 未闭合批次会标记「悬挂」">
          {(ov?.batches || []).length === 0 ? (
            <EmptyState message="暂无批次记录" />
          ) : (
            <Box sx={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
                <thead>
                  <tr style={{ color: COLORS.sub, textAlign: 'right' }}>
                    {['batch_id', 'started_at', 'finished_at', 'mode', 'scope', 'status', 'rows_loaded', 'rows_rejected'].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: '7px 10px',
                          borderBottom: `1px solid ${COLORS.border}`,
                          textAlign: h === 'batch_id' || h === 'started_at' || h === 'finished_at' ? 'left' : 'right',
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(ov?.batches || []).map((b, i) => {
                    // 未闭合（有 started 无 finished 却已非运行态，或 running 但无 finished）
                    const orphan = !!b.started_at && !b.finished_at;
                    return (
                      <tr key={i}>
                        <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, color: COLORS.text }}>
                          {b.batch_id}
                          {orphan && (
                            <Tooltip title="该批次有 started_at 但无 finished_at。若对应进程已退出，即属「悬挂批次」——状态会永久停留在 running，需人工核对（见 T05 缺陷）。">
                              <span style={{ color: COLORS.gold, fontSize: 10, marginLeft: 6 }}>未闭合</span>
                            </Tooltip>
                          )}
                        </td>
                        <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, color: COLORS.sub }}>
                          {b.started_at || '—'}
                        </td>
                        <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, color: orphan ? COLORS.gold : COLORS.sub }}>
                          {b.finished_at || '—'}
                        </td>
                        <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, textAlign: 'right' }}>
                          {b.mode}
                        </td>
                        <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, textAlign: 'right' }}>
                          {b.scope}
                        </td>
                        <td
                          style={{
                            padding: '6px 10px',
                            borderBottom: `1px solid ${COLORS.split}`,
                            textAlign: 'right',
                            color: b.status === 'success' || b.status === 'ok' ? COLORS.down : b.status === 'partial' ? COLORS.gold : COLORS.up,
                          }}
                        >
                          {b.status}
                        </td>
                        <td style={{ padding: '6px 10px', borderBottom: `1px solid ${COLORS.split}`, textAlign: 'right' }}>
                          {fmtNum(b.rows_loaded)}
                        </td>
                        <td
                          style={{
                            padding: '6px 10px',
                            borderBottom: `1px solid ${COLORS.split}`,
                            textAlign: 'right',
                            color: b.rows_rejected ? COLORS.up : COLORS.sub,
                          }}
                        >
                          {fmtNum(b.rows_rejected)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Box>
          )}
        </Card>
      </Box>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress size={18} sx={{ color: COLORS.accent }} />
        </Box>
      )}
    </div>
  );
}
