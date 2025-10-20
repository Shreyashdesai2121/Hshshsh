import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import { WebSocketProvider } from './contexts/WebSocketContext'
import { ApiProvider } from './contexts/ApiContext'

function App() {
  return (
    <Router>
      <ApiProvider>
        <WebSocketProvider>
          <div className="min-h-screen bg-gray-50">
            <Routes>
              <Route path="/" element={<Dashboard />} />
            </Routes>
          </div>
        </WebSocketProvider>
      </ApiProvider>
    </Router>
  )
}

export default App