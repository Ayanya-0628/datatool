# AGENTS.md instructions for E:\SlyLab

## 全局规则

唯一全局事实源：
- `C:\Users\16342\AGENTS.md`

开始任务读取顺序：
1. 先读本文件。
2. 再读 `progress.md`。
3. 必要时读 `README.md`、`docs/DEPLOY.md`、`docs/CODEMAPS/INDEX.md`。

说明：
- `.sisyphus/` 是旧工具残留，只作为历史记录参考；新任务不再新建或强依赖 `.sisyphus`。

## 版本记录规范

### 1. 存档操作
**触发指令**: 当提及 "存档" 或 "提交" 时

- **检查改动**: 运行 `git diff` 检查本次改动内容
- **提交代码**: 执行 `git add .` 和 `git commit`（根据改动内容自动生成 commit message）
- **更新日志**: 在 `CHANGELOG.md` 文件顶部添加记录，格式如下：

```markdown
## YYYY-MM-DD HH:mm
- 改动内容描述...
```

### 2. 回退操作
**触发指令**: 当提及 "回退" 或 "撤销" 时

- **确认目标**: 先提示将回退到哪个版本（显示上一次的提交信息）
- **等待确认**: 等待用户确认后，再执行回退操作
- **记录回退**: 回退完成后，在 `CHANGELOG.md` 文件顶部添加记录，格式如下：

```markdown
## YYYY-MM-DD HH:mm
回退: 撤销了 xxx 改动
```

### 3. 查看历史
**触发指令**: 当提及 "历史" 或 "记录" 时

- **显示记录**: 显示最近 5 次提交的简要信息

