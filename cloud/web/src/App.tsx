import { useEffect } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { connectBus, disconnectBus } from './lib/ws'
import { Dashboard } from './views/Dashboard'
import { Onboarding } from './views/Onboarding/Onboarding'
import { Welcome } from './views/Welcome'

export default function App() {
  useEffect(() => {
    connectBus()
    return () => disconnectBus()
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/watch" element={<Dashboard />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route
          path="*"
          element={
            <div className="p-8">
              <p>Not found.</p>
              <Link to="/">Start</Link>
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
