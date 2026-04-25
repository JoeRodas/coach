import { Link, NavLink, Route, Routes } from "react-router-dom";
import AnalyzePage from "./pages/AnalyzePage";
import MetricsPage from "./pages/MetricsPage";
import PlayPage from "./pages/PlayPage";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm transition-colors ${
    isActive ? "text-slate-900 font-medium" : "text-slate-600 hover:text-slate-900"
  }`;

export default function App() {
  return (
    <div className="min-h-full bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Coach
          </Link>
          <div className="flex items-center gap-5">
            <NavLink to="/play" className={navLinkClass}>
              Play
            </NavLink>
            <NavLink to="/" end className={navLinkClass}>
              Analyze
            </NavLink>
            <NavLink to="/admin/metrics" className={navLinkClass}>
              Admin · Metrics
            </NavLink>
          </div>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Routes>
          <Route path="/" element={<AnalyzePage />} />
          <Route path="/play" element={<PlayPage />} />
          <Route path="/admin/metrics" element={<MetricsPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}

function NotFound() {
  return (
    <div className="py-20 text-center text-slate-500">
      <p>Not found.</p>
    </div>
  );
}
