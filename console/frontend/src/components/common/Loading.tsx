import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';

/** 加载态：居中进度环 + 文案。 */
export default function Loading({ label = '加载中…' }: { label?: string }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5, py: 6 }}>
      <CircularProgress size={32} sx={{ color: '#58a6ff' }} />
      <Typography sx={{ color: '#8b949e', fontSize: 13 }}>{label}</Typography>
    </Box>
  );
}
