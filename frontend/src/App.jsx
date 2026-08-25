import { Navigate, Route, Routes } from "react-router-dom"

import AppShell from "@/components/AppShell"
import About from "@/pages/About"
import Ask from "@/pages/Ask"
import Browse from "@/pages/Browse"

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/ask" replace />} />
        <Route path="/ask" element={<Ask />} />
        <Route path="/browse" element={<Browse />} />
        <Route path="/about" element={<About />} />
      </Route>
    </Routes>
  )
}

export default App