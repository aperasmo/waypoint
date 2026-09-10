import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

import App from "./App.jsx"
import "./index.css"

// One shared client owns TanStack Query's server-state cache.
const queryClient = new QueryClient()

// React 18's new root API is used to enable concurrent features.
// Waypoint starts here by rendering the App component inside a BrowserRouter and QueryClientProvider.
createRoot(document.getElementById("root")).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)