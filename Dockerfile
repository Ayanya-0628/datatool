# 使用官方 Python 3.10 镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装 (利用缓存层，使用服务器专用依赖)
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# 设置 matplotlib 无 GUI 后端
ENV MPLBACKEND=Agg

# 复制当前目录下的所有文件到容器中
COPY . .

# 暴露 7860 端口 (ModelScope 强制要求)
EXPOSE 7860

# 启动 Flask 应用
# 绑定到 0.0.0.0:7860，使用 gunicorn 运行
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
