import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import About from "./pages/About";
import AppPage from "./pages/AppPage";
import Docs from "./pages/Docs";
import Layout from "./components/Layout";

// 与 vite base 一致：挂到主站子路径 /wisdom-prompt 时使用 basename；本地单独开发 VITE_BASE_PATH=/ 时为空
const base = import.meta.env.VITE_BASE_PATH ?? "/wisdom-prompt/";
const basename = base.replace(/\/$/, "") || "/";

function App() {
  return (
    <BrowserRouter basename={basename}>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/app" element={<AppPage />} />
          <Route path="/docs" element={<Docs />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
