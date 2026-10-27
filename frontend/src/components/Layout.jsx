import { Outlet } from 'react-router-dom'

import Navbar from './Navbar.jsx'
import BudgetAssistantWidget from './BudgetAssistantWidget.jsx'

export default function Layout() {
  return (
    <div className="min-h-screen bg-background text-fg">
      <Navbar />
      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
      <BudgetAssistantWidget />
    </div>
  )
}
