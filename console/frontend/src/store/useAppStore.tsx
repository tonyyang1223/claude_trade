import React, { createContext, useContext, useEffect, useState } from 'react';

/**
 * 轻量全局状态（React Context）：仅存跨页面共享的数据日期。
 * - date: 当前数据日期（'latest' 表示最新），持久化到 localStorage。
 */
interface AppState {
  date: string;
  setDate: (d: string) => void;
}

const AppStoreContext = createContext<AppState | null>(null);

const STORAGE_KEY = 'ct_console_date';

export function AppStoreProvider({ children }: { children: React.ReactNode }) {
  const [date, setDateState] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) || 'latest',
  );

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, date);
  }, [date]);

  return (
    <AppStoreContext.Provider value={{ date, setDate: setDateState }}>
      {children}
    </AppStoreContext.Provider>
  );
}

export function useAppStore(): AppState {
  const ctx = useContext(AppStoreContext);
  if (!ctx) throw new Error('useAppStore must be used within AppStoreProvider');
  return ctx;
}
