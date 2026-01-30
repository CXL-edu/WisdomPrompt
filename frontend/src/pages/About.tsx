import { Link } from "react-router-dom";

export default function About() {
  return (
    <div className="page-container pb-20 pt-14">
      <div className="card p-8 sm:p-10 fade-up">
        <div className="space-y-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">关于我们</p>
            <h1 className="font-display text-3xl font-semibold text-slate-900 sm:text-4xl">
              让检索与写作像思考一样顺滑。
            </h1>
          </div>
          <p className="text-base leading-relaxed text-slate-600">
            WisdomPrompt 是一个聚合联网搜索与向量知识库的智能问答产品。它会先拆解问题，再并行检索和整理，
            最终生成可直接使用的答案与提示词，帮助你更快完成研究、写作与方案输出。
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="card-tight p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">技术栈</p>
              <p className="mt-2 text-sm text-slate-600">
                Vite + React + Tailwind，后端 FastAPI + DuckDB + VSS，LLM（OpenAI）、Embedding（Gemini）。
              </p>
            </div>
            <div className="card-tight p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">适用场景</p>
              <p className="mt-2 text-sm text-slate-600">
                市场研究、竞品对比、技术调研、产品规划与知识库协作。
              </p>
            </div>
          </div>
          <Link to="/app" className="btn-primary w-fit">
            前往产品页
          </Link>
        </div>
      </div>
    </div>
  );
}
