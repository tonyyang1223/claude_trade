import type { ReactNode } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { COLORS } from '../../theme';

interface Props {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}

/** 页面标题区：主标题 + 副标题 + 右侧操作位。 */
export default function PageHeader({ title, subtitle, actions }: Props) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', mb: 2, gap: 2, flexWrap: 'wrap' }}>
      <Box>
        <Typography variant="h5" sx={{ fontWeight: 700, color: COLORS.text }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography sx={{ color: COLORS.sub, fontSize: 13, mt: 0.5 }}>{subtitle}</Typography>
        )}
      </Box>
      {actions && <Box>{actions}</Box>}
    </Box>
  );
}
