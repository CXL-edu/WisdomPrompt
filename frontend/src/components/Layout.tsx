import { Link } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <nav className="border-b border-slate-200 bg-white px-4 py-3 flex gap-6 items-center">
        <Link to="/" className="font-semibold text-slate-800 hover:text-slate-600">
          WisdomPrompt
        </Link>
        <Link to="/about" className="text-slate-600 hover:text-slate-900">
          介绍
        </Link>
        <Link to="/app" className="text-slate-600 hover:text-slate-900">
          产品
        </Link>
        <Link to="/docs" className="text-slate-600 hover:text-slate-900">
          文档
        </Link>
      </nav>
      <main className="flex-1">{children}</main>
    </div>
  );
}
