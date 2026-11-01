# Prisk-System Frontend

本目录是独立的 Next.js 工作区，包含页面、组件、静态资源、构建配置和 npm 锁文件。它只通过 `next.config.ts` 的 rewrite 访问本地 Python API，不直接读取 Git 仓库或阶段数据。

从仓库根目录运行：

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

API 默认地址为 `http://127.0.0.1:8765`，页面默认地址为 `http://localhost:3000`。
