import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { HomePage } from '@/pages/HomePage'
import { GamePage } from '@/pages/GamePage'
import { SpectatePage } from '@/pages/SpectatePage'
import { LeaderboardPage } from '@/pages/LeaderboardPage'
import { StatsPage } from '@/pages/StatsPage'
import { ReplayPage } from '@/pages/ReplayPage'
import { PlayerStatsPage } from '@/pages/PlayerStatsPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout><HomePage /></Layout>} />
      <Route path="/game/:gameId" element={<GamePage />} />
      <Route path="/spectate/:gameId" element={<SpectatePage />} />
      <Route path="/leaderboard" element={<Layout><LeaderboardPage /></Layout>} />
      <Route path="/stats" element={<Layout><StatsPage /></Layout>} />
      <Route path="/replay/:gameId" element={<Layout><ReplayPage /></Layout>} />
      <Route path="/player/:playerId" element={<Layout><PlayerStatsPage /></Layout>} />
    </Routes>
  )
}

export default App
