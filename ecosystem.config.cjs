/**
 * PM2 进程配置：WisdomPrompt 前端与后端
 * 使用前请先：后端安装依赖并创建 .venv，前端 npm run build
 * 启动：pm2 start ecosystem.config.cjs
 */
const path = require('path');
const projectRoot = path.resolve(__dirname);

module.exports = {
  apps: [
    {
      name: 'wisdom-prompt-backend',
      script: path.join(projectRoot, '.venv', 'bin', 'uvicorn'),
      args: ['backend.main:app', '--host', '0.0.0.0', '--port', '8000'],
      cwd: projectRoot,
      env: { PYTHONPATH: projectRoot },
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
    },
    {
      name: 'wisdom-prompt-frontend',
      script: 'server.mjs',
      cwd: path.join(projectRoot, 'frontend'),
      interpreter: 'node',
      env: { PORT: '5173' },
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
    },
  ],
};
