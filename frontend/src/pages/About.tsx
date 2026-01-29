import { Link } from "react-router-dom";

export default function About() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">关于 WisdomPrompt</h1>
      <p className="text-slate-600 leading-relaxed mb-4">
        品牌与功能说明页。提供联网搜索、向量知识库检索，以及基于检索结果的提示词与答案生成。
      </p>
      <p className="text-slate-600 leading-relaxed mb-6">
        技术栈：Vite + React + Tailwind，后端 FastAPI + DuckDB + VSS，LLM（OpenAI）、Embedding（Gemini）。
      </p>
      <Link to="/app" className="text-slate-700 font-medium hover:text-slate-900 underline">
        前往产品页
      </Link>
    </div>
  );
}
