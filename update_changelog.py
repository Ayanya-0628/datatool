import os
import datetime

changelog_path = 'e:/AntiAPP/CHANGELOG.md'
if os.path.exists(changelog_path):
    with open(changelog_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
else:
    content = ""

new_entry = f"""## {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
- **重构**: 替换并集成全新的基于 Tailwind CSS 的数据分析看板与变量选择 Modal (Variable Picker) 设计
  - 移除了依赖旧式 .hidden 类导致的闪烁和冲突，平滑过渡了基于 `display: flex` 的响应式加载视图
  - 重新设计并替换了整个 `dashboard.html`，保留原有的 ID 钩子以实现零后端修改无缝接入
  - 重载并修正了原 `app.js` 生成的部分 DOM 样式（例如：Transfer 列表卡片、分析结果 Tabs 按钮框的边距、边框和选中态）

"""

with open(changelog_path, 'w', encoding='utf-8') as f:
    f.write(new_entry + content)
