import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { COLORS } from '../../theme';

/** 空态：无数据时的友好占位。 */
export default function EmptyState({ message = '暂无数据', hint }: { message?: string; hint?: string }) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 6,
        color: COLORS.sub,
        border: `1px dashed ${COLORS.border}`,
        borderRadius: 2,
      }}
    >
      <Typography sx={{ fontSize: 14 }}>{message}</Typography>
      {hint && (
        <Typography sx={{ fontSize: 12, mt: 0.5, opacity: 0.8 }}>{hint}</Typography>
      )}
    </Box>
  );
}
