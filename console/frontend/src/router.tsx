import { Routes, Route, Navigate } from 'react-router-dom';
import MarketOverview from './pages/MarketOverview';
import TokenProfile from './pages/TokenProfile';
import Comparison from './pages/Comparison';
import Onchain from './pages/Onchain';
import ScoresAdvice from './pages/ScoresAdvice';
import HundredXRadar from './pages/HundredXRadar';

/** 路由表：6 个投研面板。 */
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/market" replace />} />
      <Route path="/market" element={<MarketOverview />} />
      <Route path="/token/:id" element={<TokenProfile />} />
      <Route path="/compare" element={<Comparison />} />
      <Route path="/onchain" element={<Onchain />} />
      <Route path="/scores" element={<ScoresAdvice />} />
      <Route path="/scores/:id" element={<ScoresAdvice />} />
      <Route path="/radar" element={<HundredXRadar />} />
      <Route path="*" element={<Navigate to="/market" replace />} />
    </Routes>
  );
}
