import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { COLORS } from '../../theme';

/**
 * 强制免责声明 —— 每个页面底部展示（实现要求：前端每个页面底部必须强制展示）。
 * 同时为数据源给出说明。
 */
export default function RiskDisclaimer() {
  return (
    <Box
      component="footer"
      sx={{
        borderTop: `1px solid ${COLORS.border}`,
        bgcolor: COLORS.bg,
        px: { xs: 2, md: 3 },
        py: 1.5,
      }}
    >
      <Typography sx={{ color: COLORS.sub, fontSize: 12, lineHeight: 1.6 }}>
        风险提示：以上仅为基于公开数据的整理，不构成任何投资建议。加密资产波动剧烈，可能造成全部本金损失，请自行研究并谨慎决策，风险自担。
      </Typography>
    </Box>
  );
}
