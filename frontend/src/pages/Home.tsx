import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="page-container pb-20 pt-16">
      <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div className="space-y-8 fade-up">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            智能问答引擎
          </div>
          <h1 className="font-display text-4xl font-semibold leading-tight text-slate-900 sm:text-5xl lg:text-6xl">
            WisdomPrompt
            <span className="block text-slate-500">把复杂问题拆成清晰答案。</span>
          </h1>
          <p className="max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
            联网搜索、知识库检索与提示词生成合成一条连续工作流，让你快速定位可信信息、整理要点，并输出可复用的结论。
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/app" className="btn-primary">
              立即体验
            </Link>
            <Link to="/about" className="btn-secondary">
              了解产品
            </Link>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-slate-500">
            <span className="badge">检索自动化</span>
            <span className="badge">可编辑子任务</span>
            <span className="badge">答案可复制</span>
          </div>
        </div>
        <div className="card p-6 sm:p-8 fade-up">
          <div className="space-y-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">工作流</p>
              <h2 className="font-display text-2xl font-semibold text-slate-900">从问题到答案的 4 步。</h2>
            </div>
            <ol className="space-y-4 text-sm text-slate-600">
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-blue-500" />
                <div>
                  <p className="font-semibold text-slate-800">任务分解</p>
                  <p>把问题拆成可检索的子任务。</p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-slate-400" />
                <div>
                  <p className="font-semibold text-slate-800">检索聚合</p>
                  <p>并行抓取多来源证据与原文。</p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-slate-400" />
                <div>
                  <p className="font-semibold text-slate-800">摘要整理</p>
                  <p>输出每个子任务的要点摘要。</p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-slate-400" />
                <div>
                  <p className="font-semibold text-slate-800">答案生成</p>
                  <p>合并结果，形成结构化最终回答。</p>
                </div>
              </li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
