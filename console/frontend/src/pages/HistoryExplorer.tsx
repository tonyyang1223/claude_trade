import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import InputAdornment from '@mui/material/InputAdornment';
import { getCategoriesTimeline, getMacroHistorySeries, searchHistory, softMiss } from '../api/history';
import type { CategoryTimelinePoint, MacroSeriesPoint, SearchResponse } from '../types/history';
import { useAppStore } from '../store/useAppStore';
import { COLORS } from '../theme';
import { fmtPct, fmtNum } from '../utils/format';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import Loading from '../components/common/Loading';
import EmptyState from '../components/common/EmptyState';
import HeatMap from '../components/charts/HeatMap';
import LineChart from '../components/charts/LineChart';
import ArchiveTimeline from '../components/history/ArchiveTimeline';

const PAGE_SIZE = 50;

/**
 * 历史检索页（场景② 叙事与新闻时间线 + 全文检索）。
 *
 * 四块内容：
 * 1. **全文检索（H5）** —— CJK bigram → FTS(OR) → ILIKE 兜底；标注命中来源（FTS 有分 / ILIKE 无分）；
 * 2. **归档时间线（H4）** —— 按币种 / 来源 / 日期区间过滤；
 * 3. **板块历史演变（H3）** —— 日期 × 板块平均涨跌热力图；
 * 4. **宏观历史（H8）** —— BTC 占比、恐惧贪婪指数时序。
 *
 * 硬约定：**无结果就是无结果**——界面给出明确提示，绝不回退到「猜一个相关结果」或伪造摘要。
 */
export default function HistoryExplorer() {
  const { date, dates } = useAppStore();

  // 支持深链：/history?q=Solana&coin_id=bitcoin&source=v2ex
  // 既是「可分享/可收藏的检索链接」，也让这条渲染路径可被真机验证。
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQ = searchParams.get('q') || '';

  // ---------------- H5 检索状态 ----------------
  const [q, setQ] = useState(initialQ);
  const [submitted, setSubmitted] = useState(initialQ);
  const [coinFilter, setCoinFilter] = useState(searchParams.get('coin_id') || '');
  const [sourceFilter, setSourceFilter] = useState(searchParams.get('source') || '');
  const [useRange, setUseRange] = useState(searchParams.get('range') === '1');
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [search, setSearch] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchErr, setSearchErr] = useState<string | null>(null);

  // ---------------- H3 板块 ----------------
  const [catRows, setCatRows] = useState<CategoryTimelinePoint[]>([]);
  const [catErr, setCatErr] = useState<string | null>(null);

  // ---------------- H8 宏观 ----------------
  const [btcDom, setBtcDom] = useState<MacroSeriesPoint[]>([]);
  const [fng, setFng] = useState<MacroSeriesPoint[]>([]);

  const earliest = dates.length ? dates[0].date : '';
  const rangeFrom = useRange ? earliest : undefined;
  const rangeTo = useRange ? date || undefined : undefined;

  // H3 板块时间线：跟随全局日期区间的「始 → 当前日」
  useEffect(() => {
    let alive = true;
    setCatErr(null);
    getCategoriesTimeline({ from: rangeFrom, to: rangeTo })
      .then((d) => alive && setCatRows(d.series || []))
      .catch((e: any) => {
        if (!alive) return;
        if (softMiss(e)) setCatRows([]);
        else setCatErr(e?.message || '板块历史加载失败');
      });
    return () => {
      alive = false;
    };
  }, [rangeFrom, rangeTo]);

  // H8 宏观历史（全量，两个指标各一条）
  useEffect(() => {
    let alive = true;
    getMacroHistorySeries('btc_dominance')
      .then((d) => alive && setBtcDom(d.series || []))
      .catch(() => alive && setBtcDom([]));
    getMacroHistorySeries('fear_greed')
      .then((d) => alive && setFng(d.series || []))
      .catch(() => alive && setFng([]));
    return () => {
      alive = false;
    };
  }, []);

  const runSearch = (query: string, nextLimit = PAGE_SIZE) => {
    const term = query.trim();
    setSubmitted(term);
    // 同步到 URL：使检索结果可分享 / 可收藏（刷新后仍复现同一次检索）
    const p = new URLSearchParams();
    if (term) p.set('q', term);
    if (coinFilter) p.set('coin_id', coinFilter);
    if (sourceFilter) p.set('source', sourceFilter);
    if (useRange) p.set('range', '1');
    setSearchParams(p, { replace: true });

    if (!term) {
      setSearch(null);
      setSearchErr(null);
      return;
    }
    setSearching(true);
    setSearchErr(null);
    searchHistory(term, {
      from: rangeFrom,
      to: rangeTo,
      coin_id: coinFilter || undefined,
      source: sourceFilter || undefined,
      limit: nextLimit,
      offset: 0,
    })
      .then((d) => {
        setSearch(d);
        setLimit(nextLimit);
      })
      .catch((e: any) => setSearchErr(e?.message || '检索失败'))
      .finally(() => setSearching(false));
  };

  // 依赖 rangeFrom / rangeTo / 过滤条件变化自动重跑（切日期时结果随之更新）
  useEffect(() => {
    if (submitted.trim()) runSearch(submitted, limit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rangeFrom, rangeTo, coinFilter, sourceFilter]);

  const ftsCount = search?.hits.filter((h) => h.score != null).length || 0;
  const ilikeCount = (search?.hits.length || 0) - ftsCount;

  // ---------------- H3 热力图数据 ----------------
  const { heatX, heatY, heatData, topCats } = useMemo(() => {
    const allDates = Array.from(new Set(catRows.map((r) => r.date))).sort();
    const totals = new Map<string, number>();
    catRows.forEach((r) => totals.set(r.category, (totals.get(r.category) || 0) + r.coin_count));
    const cats = Array.from(totals.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([c]) => c);
    const catIndex = new Map(cats.map((c, i) => [c, i]));
    const dateIndex = new Map(allDates.map((d, i) => [d, i]));
    const data: [number, number, number][] = [];
    catRows.forEach((r) => {
      const ci = catIndex.get(r.category);
      const di = dateIndex.get(r.date);
      if (ci === undefined || di === undefined) return;
      if (r.avg_chg === null || r.avg_chg === undefined) return;
      data.push([di, ci, r.avg_chg]);
    });
    return { heatX: allDates, heatY: cats, heatData: data, topCats: cats.length };
  }, [catRows]);

  const macroX = btcDom.map((p) => (p.snapshot_at || '').slice(0, 10));
  const fngX = fng.map((p) => (p.snapshot_at || '').slice(0, 10));

  return (
    <div>
      <PageHeader
        title="历史检索"
        subtitle={`历史库全文检索 + 归档时间线 + 板块演变 + 宏观历史 · 当前数据日期 ${date || '后端缺省'} · 日历 ${dates.length} 天`}
      />

      {/* ---------------- H5 全文检索 ---------------- */}
      <Card
        title="全文检索"
        subtitle="H5 · content_archive · 中文 bigram 化后走 FTS(OR)，0 命中回退 ILIKE"
        actions={
          <Chip
            size="small"
            label={useRange ? '限当前区间' : '全库范围'}
            onClick={() => setUseRange((v) => !v)}
            sx={{
              fontSize: 11,
              bgcolor: useRange ? 'rgba(88,166,255,0.18)' : 'transparent',
              color: useRange ? COLORS.accent : COLORS.sub,
              border: `1px solid ${useRange ? COLORS.accent : COLORS.border}`,
            }}
          />
        }
      >
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center', mb: 1.5 }}>
          <TextField
            size="small"
            placeholder="关键词，如 Solana / 哔哩哔哩 / ETF"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') runSearch(q, PAGE_SIZE);
            }}
            sx={{ minWidth: 300, '& .MuiOutlinedInput-notchedOutline': { borderColor: COLORS.border } }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <Button size="small" variant="text" onClick={() => runSearch(q, PAGE_SIZE)}>
                    搜索
                  </Button>
                </InputAdornment>
              ),
            }}
          />
          <TextField
            size="small"
            label="币种 ID（可选）"
            value={coinFilter}
            onChange={(e) => setCoinFilter(e.target.value)}
            sx={{ width: 180, '& .MuiOutlinedInput-notchedOutline': { borderColor: COLORS.border } }}
          />
          <TextField
            size="small"
            label="来源（可选）"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            sx={{ width: 160, '& .MuiOutlinedInput-notchedOutline': { borderColor: COLORS.border } }}
          />
          <Button
            variant="contained"
            size="small"
            disabled={!q.trim() || searching}
            onClick={() => runSearch(q, PAGE_SIZE)}
            sx={{ bgcolor: COLORS.accent, color: COLORS.bg }}
          >
            {searching ? '检索中…' : '检索'}
          </Button>
        </Box>

        <Box sx={{ mb: 1.5, p: 1, borderRadius: 1, bgcolor: 'rgba(139,148,158,0.08)', fontSize: 11.5, color: COLORS.sub, lineHeight: 1.7 }}>
          语料口径说明：中文召回受采集侧语料构成限制 —— 部分中文词（如「以太坊」「治理」）在任何分词/兜底方案下均为 0，
          属历史归档源以英文来源为主所致，并非检索故障；若命中文，会标注是 FTS 打分命中还是 ILIKE 兜底命中。
        </Box>

        {searching && <Loading label="检索中…" />}
        {!searching && searchErr && <EmptyState message="检索失败" hint={searchErr} />}

        {!searching && !searchErr && search && (
          <>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center', mb: 1 }}>
              <Typography sx={{ color: COLORS.text, fontSize: 13 }}>
                查询「{search.query || submitted}」命中 <b>{fmtNum(search.total)}</b> 行
                （content_archive 为「文档×币」行级归档，同篇文章会按相关币重复计数），
                本页 {search.hits.length} 行
              </Typography>
              <Typography sx={{ color: COLORS.sub, fontSize: 11 }}>耗时 {search.took_ms} ms</Typography>
              {ftsCount > 0 && (
                <Chip size="small" label={`FTS 打分 ${ftsCount}`} sx={{ fontSize: 10, height: 18, bgcolor: 'rgba(46,189,133,0.15)', color: COLORS.down }} />
              )}
              {ilikeCount > 0 && (
                <Chip size="small" label={`ILIKE 兜底 ${ilikeCount}`} sx={{ fontSize: 10, height: 18, bgcolor: 'rgba(226,178,3,0.15)', color: COLORS.gold }} />
              )}
            </Box>

            {search.hits.length === 0 ? (
              <EmptyState
                message="无匹配结果"
                hint="FTS 与 ILIKE 均为 0 命中。这不是错误：请换用更短的关键词（中文建议 2 字以上），或放宽币种/来源/日期过滤。"
              />
            ) : (
              <Box sx={{ maxHeight: 520, overflow: 'auto' }}>
                {search.hits.map((h, i) => (
                  <Box key={`${h.content_id}-${i}`} sx={{ py: 1, borderBottom: `1px solid ${COLORS.split}` }}>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'baseline', flexWrap: 'wrap' }}>
                      {h.url ? (
                        <a href={h.url} target="_blank" rel="noreferrer" style={{ color: COLORS.text, fontSize: 13, flex: 1, minWidth: 220, textDecoration: 'none' }}>
                          {h.title || '(无标题)'}
                        </a>
                      ) : (
                        <Typography sx={{ color: COLORS.text, fontSize: 13, flex: 1, minWidth: 220 }}>
                          {h.title || '(无标题)'}
                        </Typography>
                      )}
                      {h.score != null && (
                        <Typography sx={{ color: COLORS.down, fontSize: 11 }}>bm25 {h.score.toFixed(2)}</Typography>
                      )}
                      {h.score == null && (
                        <Typography sx={{ color: COLORS.gold, fontSize: 11 }}>ILIKE</Typography>
                      )}
                    </Box>
                    <Typography sx={{ color: COLORS.sub, fontSize: 11.5, mt: 0.5, lineHeight: 1.6 }}>
                      {h.snippet || '(无摘要)'}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.75, mt: 0.5, flexWrap: 'wrap' }}>
                      {h.date && <Chip size="small" label={h.date} sx={{ fontSize: 10, height: 18 }} />}
                      {h.coin_id && <Chip size="small" label={h.coin_id} sx={{ fontSize: 10, height: 18, bgcolor: 'rgba(163,113,247,0.12)', color: COLORS.purple }} />}
                      {h.source && <Chip size="small" label={h.source} sx={{ fontSize: 10, height: 18, bgcolor: 'rgba(88,166,255,0.12)', color: COLORS.accent }} />}
                      {h.origin_path && (
                        <Typography sx={{ color: COLORS.sub, fontSize: 10, alignSelf: 'center' }}>{h.origin_path}</Typography>
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>
            )}

            {search.hits.length > 0 && search.hits.length < search.total && (
              <Box sx={{ mt: 1, textAlign: 'center' }}>
                <Button size="small" onClick={() => runSearch(submitted, limit + PAGE_SIZE)} disabled={searching}>
                  {searching ? '加载中…' : `加载更多（已 ${search.hits.length}/${search.total}）`}
                </Button>
              </Box>
            )}
          </>
        )}

        {!searching && !searchErr && !search && (
          <EmptyState message="输入关键词后回车或点「检索」" hint="检索范围默认全库；开启右上角「限当前区间」后随全局日期区间收窄。" />
        )}
      </Card>

      {/* ---------------- H4 归档时间线 ---------------- */}
      <Box sx={{ mt: 2 }}>
        <Card
          title="归档时间线"
          subtitle="H4 · content_archive 逐日归档（按归档日倒序）· 行级（文档×币），默认已按文档去重"
          actions={
            <Typography sx={{ color: COLORS.sub, fontSize: 11 }}>
              {coinFilter ? `币种：${coinFilter}` : '全部币种'}
            </Typography>
          }
        >
          <ArchiveTimeline coinId={coinFilter || undefined} source={sourceFilter || undefined} pageSize={20} maxHeight={420} />
        </Card>
      </Box>

      {/* ---------------- H3 板块历史演变 ---------------- */}
      <Box sx={{ mt: 2 }}>
        <Card
          title="板块历史演变"
          subtitle={`H3 · category_membership 聚合 · TOP ${topCats} 板块 × ${heatX.length} 个采集日 · 平均 24h 涨跌`}
        >
          {catErr ? (
            <EmptyState message="板块历史加载失败" hint={catErr} />
          ) : heatData.length ? (
            <HeatMap
              xCategories={heatX}
              yCategories={heatY}
              data={heatData}
              min={-12}
              max={12}
              height={Math.max(280, heatY.length * 26 + 90)}
              fmt={fmtPct}
            />
          ) : (
            <EmptyState message="暂无板块历史数据" hint="该区间内 category_membership 无有效平均涨跌样本。" />
          )}
          <Typography sx={{ color: COLORS.sub, fontSize: 11, mt: 0.5 }}>
            口径提示：本图数据来自 category_membership，只在深度研究日（scan_day 有 deep 文件的日子）有落表，
            故日期数（{heatX.length}）远少于采集日历的 28 天；空白列代表该日无板块归属数据，而非涨跌为 0。
          </Typography>
        </Card>
      </Box>

      {/* ---------------- H8 宏观历史 ---------------- */}
      <Box sx={{ mt: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Card title="BTC 占比 历史" subtitle={`H8 · macro_snapshot.global_json · ${btcDom.length} 个快照`}>
              {btcDom.length ? (
                <LineChart
                  xData={macroX}
                  series={[{ name: 'BTC 占比 (%)', data: btcDom.map((p) => (typeof p.value === 'number' ? p.value : null)), color: COLORS.gold, area: true }]}
                  yAxes={[{ formatter: (v) => `${v.toFixed(1)}%` }]}
                  height={280}
                />
              ) : (
                <EmptyState message="暂无 BTC 占比历史" />
              )}
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card title="恐惧贪婪指数 历史" subtitle={`H8 · macro_snapshot.fear_greed_json · ${fng.length} 个快照`}>
              {fng.length ? (
                <LineChart
                  xData={fngX}
                  series={[{ name: '恐惧贪婪指数', data: fng.map((p) => (typeof p.value === 'number' ? p.value : null)), color: COLORS.purple, area: true }]}
                  yAxes={[{ min: 0, max: 100, formatter: (v) => v.toFixed(0) }]}
                  height={280}
                />
              ) : (
                <EmptyState
                  message="暂无恐惧贪婪历史"
                  hint="已知数据缺口（ARCHITECTURE.md §13-O4）：宏观采集侧 fear_greed 源值恒为 null，故 macro_snapshot.fear_greed_json 全表为 NULL。ETL 如实落 NULL、不造数据，属采集侧待补，非查询故障。"
                />
              )}
            </Card>
          </Grid>
        </Grid>
      </Box>

      <Box sx={{ mt: 2, p: 1.5, borderRadius: 1, bgcolor: 'rgba(139,148,158,0.08)', color: COLORS.sub, fontSize: 12, lineHeight: 1.7 }}>
        检索结果与归档条目均为历史采集原文，不含任何模型改写或推断；缺失字段显示为「—」而非补零。
        评分（score）与社交热度未入库，故不会出现在任何历史视图中。
      </Box>
    </div>
  );
}
