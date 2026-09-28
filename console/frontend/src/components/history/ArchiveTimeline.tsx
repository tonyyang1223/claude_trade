import { useEffect, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import { getNewsTimeline, softMiss } from '../../api/history';
import type { NewsTimeline, NewsTimelineItem } from '../../types/history';
import { COLORS } from '../../theme';
import Loading from '../common/Loading';
import EmptyState from '../common/EmptyState';

interface Props {
  coinId?: string;
  category?: string;
  source?: string;
  from?: string;
  to?: string;
  pageSize?: number;
  /** 内嵌到窄卡片时的最大高度 */
  maxHeight?: number;
}

/**
 * 文档级去重键。
 *
 * `content_archive` 是 **document × coin 的行级归档**：同一篇文章会被采集端写进
 * 每个相关币的 payload（实测 39352 行 / 仅 3049 篇文档，平均挂 12.9 个币），
 * 因此直接按行展示会让同一条新闻重复 10 余次。此键把「同一文档」折叠为一条。
 *
 * 注意：去重**只作用于当前已加载页**（响应里没有全局文档 ID），
 * 所以界面上必须同时展示「行数」与「去重后篇数」两个数，不可只报其一。
 */
function docKey(it: NewsTimelineItem): string {
  return `${it.date}|${it.source}|${it.title || ''}|${it.url || ''}`;
}

/**
 * 内容归档时间线（场景② —— H4）。
 *
 * 逐条展示 `content_archive` 中的归档内容（标题 + 来源 + 归档日 + 原始路径），
 * 支持「加载更多」分页与「按文档去重」视图。**不做任何摘要生成**——
 * 只呈现库里真实存在的字段。
 */
export default function ArchiveTimeline({
  coinId,
  category,
  source,
  from,
  to,
  pageSize = 20,
  maxHeight = 380,
}: Props) {
  const [data, setData] = useState<NewsTimeline | null>(null);
  const [limit, setLimit] = useState(pageSize);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  /** 默认开启文档去重：直接按行看会被「同一新闻挂 13 个币」淹没 */
  const [dedupe, setDedupe] = useState(true);

  useEffect(() => {
    setLimit(pageSize);
  }, [pageSize, coinId, category, source, from, to]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    getNewsTimeline({ coin_id: coinId, category, source, from, to, limit })
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((e: any) => {
        if (!alive) return;
        if (softMiss(e)) {
          setData((e.data as NewsTimeline) || { items: [], total: 0 });
        } else {
          setError(e?.message || '归档内容加载失败');
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [coinId, category, source, from, to, limit]);

  /**
   * 展示项：`{ it, n }`，`n` 为同一文档在本页出现的行数（即挂了多少个币）。
   * 去重只作用于当前已加载页 —— 响应里没有全局文档 ID，故必须在界面上同时给出两个计数。
   */
  const displayItems = useMemo<{ it: NewsTimelineItem; n: number }[]>(() => {
    if (!data) return [];
    if (!dedupe) return data.items.map((it) => ({ it, n: 1 }));
    const grouped = new Map<string, { it: NewsTimelineItem; n: number }>();
    data.items.forEach((it) => {
      const key = docKey(it);
      const hit = grouped.get(key);
      if (hit) hit.n += 1;
      else grouped.set(key, { it, n: 1 });
    });
    return Array.from(grouped.values());
  }, [data, dedupe]);

  if (loading && !data) return <Loading label="加载归档内容…" />;
  if (error) return <EmptyState message="归档内容加载失败" hint={error} />;
  if (!data || !data.items.length) {
    return (
      <EmptyState
        message="所选条件下无归档内容"
        hint="历史库 content_archive 中无匹配行（后端返回 404 + 空列表），并非加载失败。"
      />
    );
  }

  return (
    <Box>
      <Box
        sx={{
          mb: 1,
          p: 1,
          borderRadius: 1,
          bgcolor: 'rgba(139,148,158,0.08)',
          fontSize: 11.5,
          color: COLORS.sub,
          lineHeight: 1.7,
        }}
      >
        归档结构是「文档 × 币」的行级记录：同一篇文章会为每个相关币各存一行
        （实测全表 39352 行 / 仅约 3049 篇文档，平均挂 12.9 个币），因此原始行数远大于文章数。
        标题为采集原文首段，长文/无标题页面会显示为正文片段——此处不做任何截断改写，仅两行折行。
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
        <Chip
          size="small"
          label={dedupe ? '按文档去重：开' : '按文档去重：关'}
          onClick={() => setDedupe((v) => !v)}
          sx={{
            fontSize: 11,
            bgcolor: dedupe ? 'rgba(88,166,255,0.18)' : 'transparent',
            color: dedupe ? COLORS.accent : COLORS.sub,
            border: `1px solid ${dedupe ? COLORS.accent : COLORS.border}`,
          }}
        />
        <Typography sx={{ color: COLORS.sub, fontSize: 11 }}>
          {dedupe
            ? `本页 ${data.items.length} 行 → 去重后 ${displayItems.length} 篇（去重仅作用于当前已加载页）`
            : `当前按原始行展示，共 ${data.items.length} 行已加载`}
        </Typography>
      </Box>

      <Box sx={{ maxHeight, overflow: 'auto' }}>
        {displayItems.map(({ it, n }, i) => (
          <Box
            key={`${it.date}-${it.coin_id}-${i}`}
            sx={{ py: 1, borderBottom: `1px solid ${COLORS.split}` }}
          >
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexWrap: 'wrap' }}>
              <Typography sx={{ color: COLORS.sub, fontSize: 11, minWidth: 78 }}>{it.date}</Typography>
              {it.url ? (
                <Typography
                  component="a"
                  href={it.url}
                  target="_blank"
                  rel="noreferrer"
                  sx={{
                    color: COLORS.text,
                    fontSize: 13,
                    textDecoration: 'none',
                    flex: 1,
                    minWidth: 200,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    wordBreak: 'break-all',
                    '&:hover': { color: COLORS.accent },
                  }}
                >
                  {it.title || '(无标题)'}
                </Typography>
              ) : (
                <Typography
                  sx={{
                    color: COLORS.text,
                    fontSize: 13,
                    flex: 1,
                    minWidth: 200,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    wordBreak: 'break-all',
                  }}
                >
                  {it.title || '(无标题)'}
                </Typography>
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 0.75, mt: 0.5, ml: '86px', flexWrap: 'wrap' }}>
              <Chip
                size="small"
                label={it.source || '未知来源'}
                sx={{ fontSize: 10, height: 18, bgcolor: 'rgba(88,166,255,0.12)', color: COLORS.accent }}
              />
              {dedupe && n > 1 ? (
                <Chip
                  size="small"
                  label={`挂 ${n} 个币`}
                  sx={{ fontSize: 10, height: 18, bgcolor: 'rgba(226,178,3,0.15)', color: COLORS.gold }}
                />
              ) : (
                <Chip
                  size="small"
                  label={it.coin_id}
                  sx={{ fontSize: 10, height: 18, bgcolor: 'rgba(163,113,247,0.12)', color: COLORS.purple }}
                />
              )}
              {it.ts && (
                <Typography sx={{ color: COLORS.sub, fontSize: 10, alignSelf: 'center' }}>{it.ts}</Typography>
              )}
            </Box>
          </Box>
        ))}
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 1 }}>
        <Typography sx={{ color: COLORS.sub, fontSize: 11 }}>
          已加载 {data.items.length} / 共 {data.total} 行
          {data.total > data.items.length ? '（total 为行级计数，含文档×币展开）' : ''}
        </Typography>
        {data.items.length < data.total && (
          <Button size="small" variant="text" onClick={() => setLimit((n) => n + pageSize)} disabled={loading}>
            {loading ? '加载中…' : '加载更多'}
          </Button>
        )}
      </Box>
    </Box>
  );
}
