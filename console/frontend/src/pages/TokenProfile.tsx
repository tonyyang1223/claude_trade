import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import { useAppStore } from '../store/useAppStore';
import { getTokenDetail, postTokenResearch, getTokenTwitter, ApiError } from '../api/client';
import type { TokenDetail, WebResearch, TwitterFeed } from '../types/models';
import { COLORS } from '../theme';
import { fmtMcap, fmtPct, fmtPrice, fmtNum, colorForChange } from '../utils/format';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import Loading from '../components/common/Loading';
import EmptyState from '../components/common/EmptyState';
import CoinTrendPanel from '../components/history/CoinTrendPanel';
import ArchiveTimeline from '../components/history/ArchiveTimeline';

function Row({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75, borderBottom: `1px solid ${COLORS.split}` }}>
      <Typography sx={{ color: COLORS.sub, fontSize: 13 }}>{label}</Typography>
      <Typography sx={{ color: color || COLORS.text, fontSize: 13, fontWeight: 500 }}>{value}</Typography>
    </Box>
  );
}

export default function TokenProfile() {
  const { id = 'bitcoin' } = useParams();
  const { date } = useAppStore();
  const [detail, setDetail] = useState<TokenDetail | null>(null);
  const [research, setResearch] = useState<WebResearch | null>(null);
  const [loading, setLoading] = useState(true);
  const [researching, setResearching] = useState(false);
  const [warn, setWarn] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [twitter, setTwitter] = useState<TwitterFeed | null>(null);
  const [twitterLoading, setTwitterLoading] = useState(true);
  const [twitterError, setTwitterError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setWarn(null);
    setResearch(null);
    getTokenDetail(id, date)
      .then((d) => setDetail(d))
      .catch((e: ApiError) => setError(e.message || '加载失败'))
      .finally(() => setLoading(false));
  }, [id, date]);

  const handleResearch = () => {
    setResearching(true);
    setWarn(null);
    postTokenResearch(id)
      .then((r) => {
        setResearch(r);
        if (r.description || r.news.length) setWarn(null);
        else setWarn('实时抓取未返回新内容，已保留离线基线');
      })
      .catch((e: ApiError) => setWarn(`实时抓取失败：${e.message}，已保留离线基线`))
      .finally(() => setResearching(false));
  };

  if (loading) return <Loading label="加载币种档案…" />;
  if (error) return <EmptyState message="币种档案加载失败" hint={error} />;
  if (!detail) return <EmptyState message="未找到该币种档案" />;

  // Twitter 舆情（按币过滤，与控制台选定日期无关）：来自豆包爬取的 Twitter 数据，已入库历史库。
  useEffect(() => {
    setTwitterLoading(true);
    setTwitterError(null);
    getTokenTwitter(id)
      .then((d) => setTwitter(d))
      .catch((e: ApiError) => setTwitterError(e.message || '加载失败'))
      .finally(() => setTwitterLoading(false));
  }, [id]);

  const b = detail.basic;
  const narrative = research
    ? {
        description: research.description,
        categories: research.categories,
        officialLinks: research.officialLinks,
        communityLinks: research.communityLinks,
        sentiment: research.sentiment,
      }
    : detail.narrative;
  const social = detail.social;
  const news = research?.news?.length ? research.news : detail.news;

  return (
    <div>
      <PageHeader
        title={`${b.name || b.id} (${b.sym || ''})`}
        subtitle={`CoinGecko ID: ${b.id} · 数据源: ${research ? '实时抓取' : '离线基线'}`}
        actions={
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button component={RouterLink} to={`/scores/${b.id}`} size="small" variant="outlined" sx={{ borderColor: COLORS.border }}>
              评分与建议
            </Button>
            <Button component={RouterLink} to="/onchain" size="small" variant="outlined" sx={{ borderColor: COLORS.border }}>
              链上分析
            </Button>
            <Button
              onClick={handleResearch}
              size="small"
              variant="contained"
              disabled={researching}
              sx={{ bgcolor: COLORS.accent, color: COLORS.bg }}
            >
              {researching ? <CircularProgress size={16} sx={{ color: COLORS.bg }} /> : '实时抓取'}
            </Button>
          </Box>
        }
      />

      {warn && (
        <Box sx={{ mb: 2, p: 1, borderRadius: 1, bgcolor: 'rgba(226,178,3,0.12)', color: COLORS.gold, fontSize: 13 }}>
          {warn}
        </Box>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={5}>
          <Card title="基础指标">
            <Row label="价格" value={fmtPrice(b.price)} />
            <Row label="市值" value={fmtMcap(b.mcap)} />
            <Row label="24h 成交额" value={fmtMcap(b.vol)} />
            <Row label="市值排名" value={fmtNum(b.rank)} />
            <Row label="24h 涨跌" value={fmtPct(b.chg24)} color={colorForChange(b.chg24)} />
            <Row label="7d 涨跌" value={fmtPct(b.chg7d)} color={colorForChange(b.chg7d)} />
            <Row label="距 ATH" value={detail.athChg != null ? fmtPct(detail.athChg) : '-'} color={detail.athChg != null ? colorForChange(detail.athChg) : undefined} />
            <Row label="ATH" value={fmtPrice(detail.ath)} />
          </Card>

          <Card title="社区与情绪" sx={{ mt: 2 }}>
            <Row label="社交提及数" value={fmtNum(social.mentions)} />
            <Row label="点赞数" value={fmtNum(social.upvotes)} />
            <Row label="Reddit 订阅" value={fmtNum(social.redditSubs)} />
            <Row label="社区分" value={social.communityScore ?? '-'} />
            <Row label="新闻计数" value={fmtNum(social.newsCount)} />
            <Row label="情绪信号" value={social.signal ?? '-'} />
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card title="项目叙事">
            {narrative.categories?.length ? (
              <Box sx={{ mb: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {narrative.categories.map((c: string) => (
                  <Chip key={c} label={c} size="small" sx={{ bgcolor: 'rgba(88,166,255,0.15)', color: COLORS.accent, fontSize: 11 }} />
                ))}
              </Box>
            ) : (
              <Typography sx={{ color: COLORS.sub, fontSize: 13, mb: 1 }}>暂无分类标签（实时抓取可补全）</Typography>
            )}
            <Typography sx={{ color: COLORS.text, fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {narrative.description || '暂无项目描述（点击「实时抓取」补全叙事与官方链接）。'}
            </Typography>
            {(narrative.officialLinks && Object.keys(narrative.officialLinks).length > 0) && (
              <Box sx={{ mt: 1 }}>
                <Typography sx={{ color: COLORS.sub, fontSize: 12 }}>官方链接</Typography>
                {Object.entries(narrative.officialLinks).map(([k, v]) => (
                  <div key={k}>
                    <a href={String(v)} target="_blank" rel="noreferrer" style={{ color: COLORS.accent, fontSize: 12 }}>
                      {k}
                    </a>
                  </div>
                ))}
              </Box>
            )}
          </Card>

          <Card title={`近期动态 (${news.length})`} sx={{ mt: 2 }}>
            {news.length ? (
              <Box sx={{ maxHeight: 320, overflow: 'auto' }}>
                {news.map((n, i) => (
                  <Box key={i} sx={{ py: 1, borderBottom: `1px solid ${COLORS.split}` }}>
                    <a href={n.url || '#'} target="_blank" rel="noreferrer" style={{ color: COLORS.text, fontSize: 13, textDecoration: 'none' }}>
                      {n.title || '(无标题)'}
                    </a>
                    {n.source && <Typography sx={{ color: COLORS.sub, fontSize: 11 }}> · {n.source}</Typography>}
                  </Box>
                ))}
              </Box>
            ) : (
              <EmptyState message="暂无新闻（实时抓取可补全）" />
            )}
          </Card>

          {/* Twitter 舆情：来自豆包爬取的 Twitter 数据，已入库历史库 content_archive（按币过滤，与控制台日期无关） */}
          <Card title={`Twitter 舆情 (${twitter?.count ?? 0})`} sx={{ mt: 2 }}>
            {twitterLoading ? (
              <Loading label="加载 Twitter 舆情…" />
            ) : twitterError ? (
              <EmptyState message="Twitter 舆情加载失败" hint={twitterError} />
            ) : twitter && twitter.posts.length ? (
              <Box sx={{ maxHeight: 440, overflow: 'auto' }}>
                {twitter.posts.map((p, i) => (
                  <Box key={i} sx={{ py: 1, borderBottom: `1px solid ${COLORS.split}` }}>
                    <Box sx={{ display: 'flex', gap: 0.5, mb: 0.5, alignItems: 'center' }}>
                      {p.docType === 'event' ? (
                        <Chip label={`事件·${p.eventType ?? '未知'}`} size="small" sx={{ bgcolor: 'rgba(234,179,8,0.15)', color: COLORS.gold, fontSize: 10 }} />
                      ) : (
                        <Chip label="推文" size="small" sx={{ bgcolor: 'rgba(88,166,255,0.15)', color: COLORS.accent, fontSize: 10 }} />
                      )}
                      {p.author && <Typography sx={{ color: COLORS.sub, fontSize: 11 }}>{p.author}</Typography>}
                    </Box>
                    <Typography sx={{ color: COLORS.text, fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                      {p.text || p.title || '(无内容)'}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1.5, mt: 0.5, fontSize: 11, color: COLORS.sub, flexWrap: 'wrap' }}>
                      {p.likes != null && <span>♥ {fmtNum(p.likes)}</span>}
                      {p.retweets != null && <span>↻ {fmtNum(p.retweets)}</span>}
                      {p.publishedTs && <span>{p.publishedTs}</span>}
                      {p.url && (
                        <a href={p.url} target="_blank" rel="noreferrer" style={{ color: COLORS.accent }}>原文</a>
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>
            ) : (
              <EmptyState message="该币暂无 Twitter 舆情（未在豆包 Twitter 监控列表中）" />
            )}
          </Card>
        </Grid>
      </Grid>

      {/* 场景① 币种历史趋势（H2，缺口不插值） */}
      <Box sx={{ mt: 2 }}>
        <CoinTrendPanel coinId={b.id} />
      </Box>

      {/* 场景② 该币的历史归档内容（H4） */}
      <Box sx={{ mt: 2 }}>
        <Card
          title="历史归档内容"
          subtitle={`H4 content_archive · ${b.id}`}
        >
          <ArchiveTimeline coinId={b.id} pageSize={20} maxHeight={420} />
        </Card>
      </Box>
    </div>
  );
}
