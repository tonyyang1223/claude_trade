import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getHistoryDates } from '../api/history';
import { getMeta } from '../api/client';
import type { HistoryDateRow } from '../types/history';

/**
 * 轻量全局状态（React Context）：数据日期 + 采集日历。
 *
 * ## 日期选择的三态语义（场景④ 历史快照回溯）
 * `selection` 为界面选择值，`date` 为**实际下发给接口**的值：
 *
 * | selection   | 含义                 | date（下发值）              |
 * |-------------|----------------------|-----------------------------|
 * | `'auto'`    | 最后完整扫描日（默认）| `latestComplete`（如 08-25）|
 * | `'latest'`  | 最新扫描日（含残缺）  | `'latest'` → 后端自行解析   |
 * | `YYYY-MM-DD`| 指定历史日            | 原样下发                    |
 *
 * 「默认用最后完整日」是产品明确要求：`selection` 缺省即 `'auto'`，
 * 而非旧版的 `'latest'`。旧存储键（`ct_console_date`）语义已变，
 * 故切换为 `ct_console_date_v2`，避免历史会话里的 `'latest'` 泄漏成新默认。
 *
 * ## 降级
 * H1 不可用（历史库缺失 / 503）时自动回退到 `/api/meta` 的 `availableDates`，
 * 此时 `calendarSource='meta'`、`historyReady=false`，界面给出提示但不白屏。
 */

export type CalendarSource = 'history' | 'meta' | 'none';

export interface AppState {
  /** 界面选择值：'auto' | 'latest' | 'YYYY-MM-DD' */
  selection: string;
  /** 设置选择值（用户交互入口） */
  setSelection: (s: string) => void;
  /** 实际下发给接口的日期：selection 为 'auto' 时已解析为完整日；未就绪时为空串（后端按缺省处理） */
  date: string;

  /** H1 采集日历（降级时为 /api/meta 的日期列表） */
  dates: HistoryDateRow[];
  latest?: string | null;
  latestComplete?: string | null;
  latestMacro?: string | null;

  historyReady: boolean;
  calendarSource: CalendarSource;
  calendarLoading: boolean;
  /** H1 失败原因（降级提示用） */
  calendarError?: string | null;

  /** 残缺日集合（is_partial === true），用于「当前查看残缺日」提示 */
  partialDates: Set<string>;
}

const AppStoreContext = createContext<AppState | null>(null);

const STORAGE_KEY = 'ct_console_date_v2';
export const AUTO_SELECTION = 'auto';

function readStoredSelection(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) || AUTO_SELECTION;
  } catch {
    // 隐私模式等场景下 localStorage 可能不可用 —— 退化为内存态，不影响功能
    return AUTO_SELECTION;
  }
}

export function AppStoreProvider({ children }: { children: React.ReactNode }) {
  const [selection, setSelectionState] = useState<string>(readStoredSelection);
  const [dates, setDates] = useState<HistoryDateRow[]>([]);
  const [latest, setLatest] = useState<string | null>(null);
  const [latestComplete, setLatestComplete] = useState<string | null>(null);
  const [latestMacro, setLatestMacro] = useState<string | null>(null);
  const [historyReady, setHistoryReady] = useState(false);
  const [calendarSource, setCalendarSource] = useState<CalendarSource>('none');
  const [calendarLoading, setCalendarLoading] = useState(true);
  const [calendarError, setCalendarError] = useState<string | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, selection);
    } catch {
      /* 忽略写入失败（隐私模式） */
    }
  }, [selection]);

  useEffect(() => {
    let alive = true;
    setCalendarLoading(true);
    getHistoryDates()
      .then((h) => {
        if (!alive) return;
        setDates(h.dates || []);
        setLatest(h.latest ?? null);
        setLatestComplete(h.latest_complete ?? null);
        setLatestMacro(h.latest_macro ?? null);
        setHistoryReady(true);
        setCalendarSource('history');
        setCalendarError(null);
      })
      .catch((e: Error) => {
        if (!alive) return;
        setHistoryReady(false);
        setCalendarError(e?.message || '历史库不可用');
        // 降级：/api/meta 的日期列表（无残缺标记 → is_partial 为 null）
        getMeta()
          .then((m) => {
            if (!alive) return;
            const list = m.availableDates || [];
            setDates(
              list.map((d) => ({
                date: d,
                is_partial: null,
                deep_count: 0,
                light_count: 0,
                macro_count: 0,
              })),
            );
            setCalendarSource(list.length ? 'meta' : 'none');
            // meta 只给到日期，latest / latest_complete 均为自身。
            const top = list.length ? list[list.length - 1] : null;
            setLatest(top);
            setLatestComplete(top);
          })
          .catch(() => {
            if (!alive) return;
            setCalendarSource('none');
          });
      })
      .finally(() => {
        if (alive) setCalendarLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const setSelection = useCallback((s: string) => setSelectionState(s), []);

  const date = useMemo(() => {
    if (selection === AUTO_SELECTION) return latestComplete || '';
    return selection;
  }, [selection, latestComplete]);

  const partialDates = useMemo(() => {
    const s = new Set<string>();
    dates.forEach((d) => {
      if (d.is_partial === true) s.add(d.date);
    });
    return s;
  }, [dates]);

  const value: AppState = {
    selection,
    setSelection,
    date,
    dates,
    latest,
    latestComplete,
    latestMacro,
    historyReady,
    calendarSource,
    calendarLoading,
    calendarError,
    partialDates,
  };

  return <AppStoreContext.Provider value={value}>{children}</AppStoreContext.Provider>;
}

export function useAppStore(): AppState {
  const ctx = useContext(AppStoreContext);
  if (!ctx) throw new Error('useAppStore must be used within AppStoreProvider');
  return ctx;
}
