# SlyLab - 部署指南

## 快速启动（本地运行）

```bash
cd e:\SlyLab

# 安装依赖
pip install -r requirements.txt

# 启动应用
python app.py
```

访问 http://localhost:5000 即可使用

---

## 方式一：局域网分享（最简单）

在本地启动后，其他同局域网用户可通过你的IP访问：

```bash
# 启动（监听所有网络接口）
python -c "from app import app; app.run(host='0.0.0.0', port=5000)"
```

其他用户访问: `http://你的IP地址:5000`

---

## 方式二：部署到 Render（免费）

1. 将代码上传到 GitHub/GitLab
2. 登录 [render.com](https://render.com)
3. 点击 **New → Web Service**
4. 连接你的仓库
5. 设置：
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app`
6. 点击 Create Web Service

部署完成后获得公开URL，可分享给任何人。

---

## 方式二：部署到 Railway

1. 将代码上传到 GitHub
2. 登录 [railway.app](https://railway.app)
3. 点击 **New Project → Deploy from GitHub**
4. 选择仓库，自动部署

---

## 方式四：部署到 PythonAnywhere

1. 注册 [pythonanywhere.com](https://www.pythonanywhere.com)
2. 上传代码到 Files
3. 创建 Web App，选择 Flask
4. 配置 WSGI 文件指向 `wsgi.py`

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SECRET_KEY | 安全密钥 | 自动生成 |
| PORT | 运行端口 | 5000 |

生产环境请设置强随机 SECRET_KEY。

---

## 注意事项

- 上传的数据文件会在1小时后自动删除
- 最大支持50MB文件
- 建议使用Chrome/Edge浏览器

