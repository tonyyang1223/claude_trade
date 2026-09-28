import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import { AUTO_SELECTION, useAppStore } from '../../store/useAppStore';

/**
 * 数据日期状态条（场景④ 历史快照回溯的一部分）。
 *
 * 集中呈现三类「日期可信度」信息，避免用户误把残缺日/历史日当成最新数据：
 * 1. **日历降级** —— H1 不可用，日期列表来自 /api/meta；
 * 2. **残缺日回退** —— `latest !== latestComplete` 时说明已回退到哪个完整日；
 * 3. **当前查看日的性质** —— 残缺日告警 / 历史回看提示 / 「最新」模式的真实落点。
 *
 * 无任何异常时不渲染（保持界面干净）。
 */
export default function DateNotice() {
  const {
    selection,
    date,
    dates,
    latest,
    latestComplete,
    calendarSource,
    calendarError,
    calendarLoading,
    partialDates,
  } = useAppStore();

  if (calendarLoading) return null;

  const notices: { severity: 'warning' | 'info' | 'error'; text: string }[] = [];

  if (calendarSource === 'none') {
    notices.push({
      severity: 'warning',
      text: `采集日历不可用${calendarError ? `（${calendarError}）` : ''}，日期选择器暂无可选项；页面将按后端缺省日期展示数据。`,
    });
  } else if (calendarSource === 'meta') {
    notices.push({
      severity: 'warning',
      text: '历史库不可用，采集日历已降级自 /api/meta：无「残缺日」标记，日期粒度也可能与扫描日历不一致。',
    });
  }

  const hasFallback = !!latest && !!latestComplete && latest !== latestComplete;
  if (hasFallback && (selection === AUTO_SELECTION || selection === 'latest')) {
    const partial = dates.find((d) => d.date === latest);
    const detail = partial && partial.is_partial === true ? `（deep ${partial.deep_count}）` : '';
    notices.push({
      severity: 'info',
      text: `最新扫描日 ${latest}${detail} 为残缺日，已${selection === 'latest' ? '由后端' : ''}回退至最后完整日 ${latestComplete}。当前实际数据日期：${date || latestComplete}。`,
    });
  }

  if (date && partialDates.has(date)) {
    notices.push({
      severity: 'warning',
      text: `当前查看的 ${date} 是残缺日（采集未跑满），各页面的统计口径可能不完整，请勿据此下结论。`,
    });
  } else if (date && latestComplete && date < latestComplete && selection !== AUTO_SELECTION && selection !== 'latest') {
    notices.push({
      severity: 'info',
      text: `历史回看模式：当前数据日期 ${date}，非最新完整日 ${latestComplete}。`,
    });
  }

  if (date && latestComplete && date > latestComplete) {
    notices.push({
      severity: 'info',
      text: `当前数据日期 ${date} 晚于最后完整日 ${latestComplete}，该日采集可能尚未跑完。`,
    });
  }

  if (!notices.length) return null;

  return (
    <Box sx={{ mb: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
      {notices.map((n, i) => (
        <Alert
          key={i}
          severity={n.severity}
          variant="outlined"
          sx={{
            py: 0.25,
            fontSize: 12.5,
            bgcolor: 'rgba(22,27,34,0.6)',
            '& .MuiAlert-icon': { fontSize: 18, py: 0.25 },
            '& .MuiAlert-message': { py: 0.5 },
          }}
        >
          {n.text}
        </Alert>
      ))}
    </Box>
  );
}
