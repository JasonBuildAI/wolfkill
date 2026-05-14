import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { HomePage } from '@/pages/HomePage'
import { GamePage } from '@/pages/GamePage'
import { SpectatePage } from '@/pages/SpectatePage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout><HomePage /></Layout>} />
      <Route path="/game/:gameId" element={<GamePage />} />
      <Route path="/spectate/:gameId" element={<SpectatePage />} />
    </Routes>
  )
}

export default App
