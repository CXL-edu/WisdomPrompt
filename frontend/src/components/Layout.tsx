import { NavLink } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="page-shell">
      <div className="pointer-events-none absolute -left-24 top-24 h-64 w-64 rounded-full bg-slate-200/40 blur-3xl" />
      <div className="pointer-events-none absolute -right-32 top-0 h-72 w-72 rounded-full bg-blue-200/50 blur-3xl" />
      <nav className="nav-shell">
        <div className="page-container flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <a
              href="/"
              className="text-sm font-medium text-slate-500 hover:text-slate-700"
              title="返回数源智能主站"
            >
              数源智能
            </a>
            <span className="text-slate-300">/</span>
            <NavLink to="/" className="font-display text-xl font-semibold tracking-tight text-slate-900">
              WisdomPrompt
            </NavLink>
          </div>
          <div className="flex items-center gap-6">
            <a
              href="/product"
              className="nav-link"
              title="表格数据分析"
            >
              数据分析
            </a>
            <NavLink
              to="/about"
              className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
            >
              介绍
            </NavLink>
            <NavLink
              to="/app"
              className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
            >
              产品
            </NavLink>
            <NavLink
              to="/docs"
              className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
            >
              文档
            </NavLink>
          </div>
        </div>
      </nav>
      <main className="relative z-10 flex-1 pb-16">{children}</main>
    </div>
  );
}
