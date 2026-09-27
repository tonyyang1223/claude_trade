import type { ReactNode } from 'react';
import Paper, { PaperProps } from '@mui/material/Paper';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

interface CardProps extends Omit<PaperProps, 'title'> {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  bodySx?: object;
}

/** 玻璃拟态面板（统一深色卡片）。 */
export default function Card({ title, subtitle, actions, children, bodySx, sx, ...rest }: CardProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        bgcolor: 'rgba(22,27,34,0.85)',
        border: '1px solid #30363d',
        borderRadius: 2,
        p: 2,
        backdropFilter: 'blur(6px)',
        ...sx,
      }}
      {...rest}
    >
      {(title || actions) && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
          <Box>
            {title && (
              <Typography sx={{ fontWeight: 600, color: '#e6edf3', fontSize: 15 }}>{title}</Typography>
            )}
            {subtitle && (
              <Typography sx={{ color: '#8b949e', fontSize: 12, mt: 0.25 }}>{subtitle}</Typography>
            )}
          </Box>
          {actions}
        </Box>
      )}
      <Box sx={bodySx}>{children}</Box>
    </Paper>
  );
}
