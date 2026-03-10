# 🐍 部署到 PythonAnywhere 指南 (PythonSlyLab)

**状态：✅ 已部署成功**
**网址：** `https://lyshang.pythonanywhere.com`

---

## 🔄 如何更新代码？
当你本地修改了代码（例如修复了 Bug 或加了新功能），想同步到线上网站时，请按以下步骤操作：

### 1. 在本地电脑 (VS Code)
先将修改提交到 GitHub。打开终端（Terminal）运行：
```powershell
git add .
git commit -m "更新说明"
git push
```

### 2. 在线上控制台 (PythonAnywhere)
1. 登录 [PythonAnywhere](https://www.pythonanywhere.com/) -> 点击右上角的 **Consoles** -> 点击你的 **Bash** 控制台。
2. 输入以下命令拉取最新代码：
   ```bash
   cd datatool
   git pull
   ```
   *(如果有修改了 requirements.txt，记得运行 `workon myenv` 然后 `pip install -r requirements.txt`)*
3. 去 **Web** 页面 -> 点击右上角绿色的 **Reload** 按钮。

更新完成！

---

## 🛠️ 常用维护操作

### 网站报错怎么办？
如果网页显示 "Something went wrong"：
1. 去 **Web** 页面。
2. 往下翻找到 **Log files** 部分。
3. 点击 **Error log** 查看最新的报错信息（通常在最下面）。

### 依赖库安装
如果你在 `requirements.txt` 里加了新的库：
1. 打开 Bash 控制台。
2. 进入虚拟环境并安装：
   ```bash
   workon myenv
   pip install -r requirements.txt
   ```

