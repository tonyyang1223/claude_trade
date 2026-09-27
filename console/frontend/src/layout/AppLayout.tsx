import type { ReactNode } from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import { AppStoreProvider } from '../store/useAppStore';
import NavBar from './NavBar';
import RiskDisclaimer from '../components/common/RiskDisclaimer';

/** 全局布局：顶部导航 + 内容区 + 底部强制免责声明。 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AppStoreProvider>
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', bgcolor: '#0d1117' }}>
        <NavBar />
        <Container maxWidth={false} sx={{ flex: 1, py: 2, px: { xs: 2, md: 3 } }}>
          {children}
        </Container>
        <RiskDisclaimer />
      </Box>
    </AppStoreProvider>
  );
}
