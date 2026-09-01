import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import LiveCameras from './pages/LiveCameras'
import CameraDetail from './pages/CameraDetail'
import Alerts from './pages/Alerts'
import Events from './pages/Events'
import Settings from './pages/Settings'

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/live" element={<LiveCameras />} />
          <Route path="/cameras/:id" element={<CameraDetail />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/events" element={<Events />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </div>
  )
}
