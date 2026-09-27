import { BrowserRouter } from 'react-router-dom';
import AppLayout from './layout/AppLayout';
import AppRoutes from './router';

/**
 * 顶层组件：路由 + 全局布局（顶部导航 + 内容区）。
 * 全局日期选择器等状态由 store/useAppStore 提供。
 */
export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <AppRoutes />
      </AppLayout>
    </BrowserRouter>
  );
}

