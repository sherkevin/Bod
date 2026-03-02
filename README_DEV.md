本地开发说明

后端: FastAPI 服务
前端: 静态页面（由后端挂载）

依赖 (建议使用虚拟环境):

pip install -r backend/requirements.txt

运行后端（本机）:

python -m uvicorn backend.main:app --reload --port 8000

或使用 Docker Compose:

```bash
docker compose up --build
```

打开浏览器访问 http://localhost:8000/ 查看前端页面，点击并按住“按住说话”进行录音并上传（当前为 Mock 转写）。
