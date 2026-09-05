import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import Dashboard from './pages/Dashboard'
import Rooms from './pages/Rooms'
import RoomDetail from './pages/RoomDetail'
import Cameras from './pages/Cameras'
import LiveCameras from './pages/LiveCameras'
import CameraDetail from './pages/CameraDetail'
import Alerts from './pages/Alerts'
import Events from './pages/Events'
import Settings from './pages/Settings'

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-column">
        <Topbar />
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/rooms" element={<Rooms />} />
            <Route path="/rooms/:slug" element={<RoomDetail />} />
            <Route path="/live" element={<LiveCameras />} />
            <Route path="/cameras" element={<Cameras />} />
            <Route path="/cameras/:id" element={<CameraDetail />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/events" element={<Events />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
