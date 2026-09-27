import { BrowserRouter } from 'react-router-dom';
import AppLayout from './layout/AppLayout';
import ErrorBoundary from './components/common/ErrorBoundary';
import AppRoutes from './router';

/**
 * 顶层组件：路由 + 全局布局（顶部导航 + 内容区），并以 ErrorBoundary 兜底渲染异常。
 * 全局数据日期状态由 store/useAppStore 提供。
 */
export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <ErrorBoundary>
          <AppRoutes />
        </ErrorBoundary>
      </AppLayout>
    </BrowserRouter>
  );
}
