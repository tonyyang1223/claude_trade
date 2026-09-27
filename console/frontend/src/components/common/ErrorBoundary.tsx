import { Component } from 'react';
import type { ReactNode } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';

interface State {
  hasError: boolean;
  message?: string;
}

/** 错误边界：捕获子树渲染异常，避免整页白屏。 */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  handleRetry = () => this.setState({ hasError: false, message: undefined });

  render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ p: 3, textAlign: 'center', color: '#8b949e' }}>
          <Typography sx={{ color: '#f6465d', mb: 1 }}>页面渲染出错</Typography>
          <Typography sx={{ fontSize: 12, mb: 2 }}>{this.state.message}</Typography>
          <Button variant="outlined" size="small" onClick={this.handleRetry}>
            重试
          </Button>
        </Box>
      );
    }
    return this.props.children;
  }
}
