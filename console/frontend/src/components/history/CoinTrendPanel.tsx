import { useEffect, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import { getCoinSeries, softMiss } from '../../api/history';
import type { CoinSeries } from '../../types/history';
import { SERIES_METRIC_LABELS } from '../../types/history';
import { COLORS } from '../../theme';
import { fmtMcap, fmtPrice, fmtNum, fmtPct, colorForChange } from '../../utils/format';
import Card from '../common/Card';
import Loading from '../common/Loading';
import EmptyState from '../common/EmptyState';
import LineChart from '../charts/LineChart';
import type { LineSeries } from '../charts/LineChart';

/** 指标分组 —— 决定格式化与是否适合同轴显示。 */
const METRIC_GROUP: Record<string, 'usd' | 'pct' | 'rank'> = {
  price_usd: 'usd',
  market_cap: 'usd',
  volume_24h: 'usd',
  change_24h_pct: 'pct',
  change_7d_pct: 'pct',
  rank: 'rank',
};

const METRIC_FMT: Record<string, (v: number) => string> = {
  price_usd: fmtPrice,
  market_cap: fmtMcap,
  volume_24h: fmtMcap,
  rank: fmtNum,
  change_24h_pct: (v) => fmtPct(v),
  change_7d_pct: (v) => fmtPct(v),
};

/** 后端不在历史库中的指标 —— 显式提示不可得，而不是静默忽略。 */
const KNOWN_UNAVAILABLE: Record<string, string> = {
  score: '历史评分未落盘（评分由 scorer 运行时计算，deep_research 无 score 列）',
  social_heat: '社交热度未落盘',
};

const RANGES: { key: string; label: string; days?: number }[] = [
  { key: 'all', label: '全部' },
  { key: 'd30', label: '近 30 天', days: 30 },
  { key: 'd90', label: '近 90 天', days: 90 },
];

function shiftDays(iso: string, delta: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + delta);
  return d.toISOString().slice(0, 10);
}

interface Props {
  coinId: string;
  /** 页面上方已展示当日快照时，趋势面板可更紧凑 */
  defaultMetrics?: string[];
}

/**
 * 币种历史趋势面板（场景① —— H2）。
 *
 * 设计要点：
 * - **缺口不插值**：`present=false` 的日在图中为 `null`，曲线断开，并在卡片上显式列出缺失日；
 * - **归一化对比**：多指标同选时按「首个有效日 = 100」归一，避免不同量纲挤在一根轴上看不清；
 * - **不可得指标显式说明**：请求 score / social_heat 会进 `unavailable`，界面标注原因而非假装有数据。
 */
export default function CoinTrendPanel({ coinId, defaultMetrics = ['price_usd', 'market_cap', 'rank'] }: Props) {
  const [selected, setSelected] = useState<string[]>(defaultMetrics);
  const [range, setRange] = useState<string>('all');
  const [data, setData] = useState<CoinSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);

  const params = useMemo(() => {
    const r = RANGES.find((x) => x.key === range);
    if (range === 'all' || !r?.days) return {};
    // 用「今天」做上界，后端会自行裁剪到实际扫描日区间
    const today = new Date().toISOString().slice(0, 10);
    return { from: shiftDays(today, -r.days), to: today };
  }, [range]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    setEmpty(false);
    getCoinSeries(coinId, params, selected)
      .then((d) => {
        if (!alive) return;
        setData(d);
      })
      .catch((e: any) => {
        if (!alive) return;
        if (softMiss(e)) {
          // 该区间无数据是合法结局（后端 404 + 空结构），不是加载失败
          setData((e.data as CoinSeries) || null);
          setEmpty(true);
        } else {
          setError(e?.message || '历史数据加载失败');
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [coinId, params, selected]);

  const xData = data?.series.map((p) => p.date) || [];
  const returnedMetrics = data?.metrics || [];

  /** 逐指标取值；`present=false` → null（缺口），**不做任何填充**。 */
  const valueOf = (m: string): (number | null)[] =>
    (data?.series || []).map((p) => {
      if (!p.present) return null;
      const v = p[m];
      return typeof v === 'number' ? v : null;
    });

  const hasAnyValue = returnedMetrics.some((m) => valueOf(m).some((v) => v !== null));

  /** 归一化（首日 = 100）——仅用于多指标同图对比。 */
  const normalized = useMemo<LineSeries[]>(() => {
    if (returnedMetrics.length < 2) return [];
    return returnedMetrics.map((m, i) => {
      const raw = valueOf(m);
      const base = raw.find((v) => v !== null && v !== 0);
      return {
        name: `${SERIES_METRIC_LABELS[m] || m}（首日=100）`,
        data: raw.map((v) => (v === null || !base ? null : (v / base) * 100)),
        yAxisIndex: 0,
        color: [COLORS.accent, COLORS.gold, COLORS.purple, COLORS.cyan, COLORS.blue][i % 5],
      };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, returnedMetrics.join(',')]);

  const toggle = (m: string) => {
    setSelected((prev) => (prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m]));
  };

  return (
    <Card
      title="历史趋势"
      subtitle={`H2 coin_daily_snapshot · ${coinId}${xData.length ? ` · ${xData.length} 个采集日` : ''}`}
      actions={
        <TextField
          select
          size="small"
          value={range}
          onChange={(e) => setRange(e.target.value)}
          sx={{ width: 130, '& .MuiOutlinedInput-notchedOutline': { borderColor: COLORS.border } }}
        >
          {RANGES.map((r) => (
            <MenuItem key={r.key} value={r.key}>
              {r.label}
            </MenuItem>
          ))}
        </TextField>
      }
    >
      <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mb: 1.5 }}>
        {Object.keys(SERIES_METRIC_LABELS).map((m) => (
          <Chip
            key={m}
            size="small"
            label={SERIES_METRIC_LABELS[m]}
            onClick={() => toggle(m)}
            sx={{
              fontSize: 11,
              bgcolor: selected.includes(m) ? 'rgba(88,166,255,0.18)' : 'transparent',
              color: selected.includes(m) ? COLORS.accent : COLORS.sub,
              border: `1px solid ${selected.includes(m) ? COLORS.accent : COLORS.border}`,
            }}
          />
        ))}
      </Box>

      {loading && <Loading label="加载历史时序…" />}

      {!loading && error && <EmptyState message="历史数据加载失败" hint={error} />}

      {!loading && !error && empty && (
        <EmptyState
          message="所选区间无该币历史数据"
          hint="该币在此区间未被采集入库（后端返回 404 + 空序列），并非加载失败。"
        />
      )}

      {!loading && !error && !empty && !hasAnyValue && (
        <EmptyState message="所选指标在库中均为空" hint="请勾选其他指标（如价格 / 市值 / 排名）。" />
      )}

      {!loading && !error && hasAnyValue && (
        <Grid container spacing={2}>
          {normalized.length > 0 && (
            <Grid item xs={12}>
              <Typography sx={{ color: COLORS.sub, fontSize: 12, mb: 0.5 }}>
                归一化对比（各指标首个有效日 = 100，缺口断开不插值）
              </Typography>
              <LineChart
                xData={xData}
                series={normalized}
                height={280}
                zoom={xData.length > 40}
                yAxes={[{ name: '指数', formatter: (v) => v.toFixed(0) }]}
              />
            </Grid>
          )}

          {returnedMetrics.length === 1 &&
            returnedMetrics.map((m) => {
              const g = METRIC_GROUP[m] || 'usd';
              const fmt = METRIC_FMT[m] || fmtNum;
              return (
                <Grid item xs={12} key={m}>
                  <Typography sx={{ color: COLORS.sub, fontSize: 12, mb: 0.5 }}>
                    {SERIES_METRIC_LABELS[m] || m} 逐日走势（缺口断开）
                  </Typography>
                  <LineChart
                    xData={xData}
                    series={[
                      {
                        name: SERIES_METRIC_LABELS[m] || m,
                        data: valueOf(m),
                        color: g === 'pct' ? COLORS.gold : COLORS.accent,
                        area: true,
                      },
                    ]}
                    height={300}
                    zoom={xData.length > 40}
                    yAxes={[
                      {
                        name: g === 'rank' ? '排名（越小越好）' : undefined,
                        inverse: g === 'rank',
                        formatter: fmt,
                      },
                    ]}
                    gapDates={data?.gaps}
                  />
                </Grid>
              );
            })}

          <Grid item xs={12}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
              <Typography sx={{ color: COLORS.sub, fontSize: 12 }}>
                采集日 {xData.length} · 缺失 {data?.gaps.length || 0}
              </Typography>
              {(data?.gaps || []).slice(0, 12).map((g) => (
                <Chip
                  key={g}
                  size="small"
                  label={`缺 ${g}`}
                  sx={{ fontSize: 10, height: 18, bgcolor: 'rgba(226,178,3,0.12)', color: COLORS.gold }}
                />
              ))}
              {(data?.gaps.length || 0) > 12 && (
                <Typography sx={{ color: COLORS.sub, fontSize: 11 }}>
                  …共 {data?.gaps.length} 个缺失日
                </Typography>
              )}
            </Box>
          </Grid>

          {(data?.unavailable || []).length > 0 && (
            <Grid item xs={12}>
              <Box sx={{ p: 1, borderRadius: 1, bgcolor: 'rgba(226,178,3,0.10)', fontSize: 12, color: COLORS.gold }}>
                以下指标历史库中不可得，未以任何方式伪造：
                {(data?.unavailable || []).map((m) => (
                  <div key={m} style={{ marginTop: 2 }}>
                    · <code>{m}</code> —— {KNOWN_UNAVAILABLE[m] || '历史库无对应列'}
                  </div>
                ))}
              </Box>
            </Grid>
          )}

          <Grid item xs={12}>
            <Typography sx={{ color: COLORS.sub, fontSize: 12, mb: 0.5 }}>
              逐日原始值（缺 = 「—」，非 0）
            </Typography>
            <Box sx={{ overflowX: 'auto', maxHeight: 300, overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ color: COLORS.sub, position: 'sticky', top: 0, background: COLORS.panel }}>
                    <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: `1px solid ${COLORS.border}` }}>
                      日期
                    </th>
                    {returnedMetrics.map((m) => (
                      <th
                        key={m}
                        style={{ textAlign: 'right', padding: '6px 8px', borderBottom: `1px solid ${COLORS.border}` }}
                      >
                        {SERIES_METRIC_LABELS[m] || m}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data?.series || []).map((p) => (
                    <tr key={p.date}>
                      <td style={{ padding: '5px 8px', color: COLORS.text, borderBottom: `1px solid ${COLORS.split}` }}>
                        {p.date}
                        {!p.present && (
                          <span style={{ color: COLORS.gold, fontSize: 10, marginLeft: 6 }}>缺失</span>
                        )}
                      </td>
                      {returnedMetrics.map((m) => {
                        const v = p.present && typeof p[m] === 'number' ? (p[m] as number) : null;
                        const fmt = METRIC_FMT[m] || fmtNum;
                        const color =
                          METRIC_GROUP[m] === 'pct' ? colorForChange(v) : COLORS.text;
                        return (
                          <td
                            key={m}
                            style={{
                              textAlign: 'right',
                              padding: '5px 8px',
                              color: v === null ? COLORS.sub : color,
                              borderBottom: `1px solid ${COLORS.split}`,
                            }}
                          >
                            {v === null ? '—' : fmt(v)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Box>
          </Grid>
        </Grid>
      )}
    </Card>
  );
}
