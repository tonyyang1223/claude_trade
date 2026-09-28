import type { ReactNode } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import { AppStoreProvider } from '../store/useAppStore';
import NavBar from './NavBar';
import RiskDisclaimer from '../components/common/RiskDisclaimer';
import DateNotice from '../components/history/DateNotice';
import { COLORS } from '../theme';

/** 全局布局：顶部导航 + 数据日期状态条 + 内容区 + 底部强制免责声明。 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AppStoreProvider>
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', bgcolor: COLORS.bg }}>
        <NavBar />
        <Container maxWidth={false} sx={{ flex: 1, py: 2, px: { xs: 2, md: 3 } }}>
          <DateNotice />
          {children}
        </Container>
        <RiskDisclaimer />
      </Box>
    </AppStoreProvider>
  );
}
