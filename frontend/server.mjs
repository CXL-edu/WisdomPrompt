/**
 * 在子路径 /wisdom-prompt/ 下提供 dist 静态文件，供 nginx 代理，避免 vite preview 的重定向循环。
 * 用法：node server.mjs  或  PORT=5173 node server.mjs
 */
import { createServer } from 'http';
import { readFileSync, existsSync } from 'fs';
import { join, extname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const PORT = Number(process.env.PORT) || 5173;
const BASE = '/wisdom-prompt';
const DIST = join(__dirname, 'dist');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.ico': 'image/x-icon',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.woff2': 'font/woff2',
};

const server = createServer((req, res) => {
  let path = req.url || '/';
  const q = path.indexOf('?');
  if (q >= 0) path = path.slice(0, q);
  if (!path.startsWith(BASE)) {
    res.writeHead(404);
    res.end();
    return;
  }
  path = path.slice(BASE.length) || '/';
  let file = path === '/' ? join(DIST, 'index.html') : join(DIST, path);
  // SPA 回退：路径无扩展名且文件不存在时（如 /app、/about）返回 index.html
  if (!existsSync(file)) {
    if (extname(path)) {
      res.writeHead(404);
      res.end();
      return;
    }
    file = join(DIST, 'index.html');
    if (!existsSync(file)) {
      res.writeHead(404);
      res.end();
      return;
    }
  }
  try {
    const body = readFileSync(file);
    const mime = MIME[extname(file)] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime });
    res.end(body);
  } catch (e) {
    res.writeHead(500);
    res.end();
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`WisdomPrompt static server at http://0.0.0.0:${PORT}${BASE}/`);
});
