import React, { createContext, useContext, useEffect, useState } from 'react';

/**
 * 轻量全局状态（React Context）：仅存跨页面共享的少量状态。
 * - date: 当前数据日期（'latest' 表示最新）
 * - selectedTokens: 对比页等复用的选中币种
 * - themeMode: 预留主题切换（当前仅深色）
 */
interface AppState {
  date: string;
  setDate: (d: string) => void;
  selectedTokens: string[];
  setSelectedTokens: (ids: string[]) => void;
  themeMode: 'dark';
}

const AppStoreContext = createContext<AppState | null>(null);

const STORAGE_KEY = 'ct_console_date';

export function AppStoreProvider({ children }: { children: React.ReactNode }) {
  const [date, setDateState] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) || 'latest',
  );
  const [selectedTokens, setSelectedTokens] = useState<string[]>([]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, date);
  }, [date]);

  const setDate = (d: string) => setDateState(d);

  return (
    <AppStoreContext.Provider
      value={{ date, setDate, selectedTokens, setSelectedTokens, themeMode: 'dark' }}
    >
      {children}
    </AppStoreContext.Provider>
  );
}

export function useAppStore(): AppState {
  const ctx = useContext(AppStoreContext);
  if (!ctx) throw new Error('useAppStore must be used within AppStoreProvider');
  return ctx;
}
