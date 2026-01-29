import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-16 text-center">
      <h1 className="text-4xl font-bold text-slate-900 mb-4">WisdomPrompt</h1>
      <p className="text-lg text-slate-600 mb-8">
        联网搜索、知识库检索与提示词生成，一站式智能问答
      </p>
      <div className="flex gap-4 justify-center flex-wrap">
        <Link
          to="/app"
          className="inline-block px-6 py-3 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors"
        >
          开始使用
        </Link>
        <Link
          to="/about"
          className="inline-block px-6 py-3 border border-slate-300 rounded-lg hover:bg-slate-100 transition-colors"
        >
          了解更多
        </Link>
      </div>
    </div>
  );
}
