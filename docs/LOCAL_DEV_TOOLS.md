# Local Dev Tools

事件情报系统本地开发辅助工具。仅用于减少 token 消耗和网页抓取，**不接入生产/TG/交易链路**。

---

## 已安装工具

| 工具 | 版本 | 用途 | 安装方式 |
|------|------|------|----------|
| **rtk** | 0.42.0 | CLI 输出过滤代理，减少 LLM token 消耗 | 已有 |
| **agent-browser** | latest | 无头浏览器，AI agent 抓取网页/截图 | `npm install -g agent-browser && agent-browser install` |

---

## 验证命令

```powershell
# rtk
rtk --version       # rtk 0.42.0
rtk --help          # 查看可用子命令

# agent-browser
agent-browser --help                                      # CLI 帮助
agent-browser skills get core --full                       # 获取 AI agent 使用文档
agent-browser snapshot https://example.com                 # 截图
agent-browser fetch https://example.com --format markdown  # 抓取为 markdown
```

---

## rtk — Token 优化

rtk 是 CLI 代理，在 shell 命令输出到达 LLM 上下文之前过滤和摘要输出。
当前无需额外配置即可使用（rtk 已可被 Claude Code 调用）。

如果后续要配置 Claude Code hook 自动使用 rtk 拦截所有命令：
```
# 建议（需用户确认后执行）：
claude hooks add pre-command rtk
```
**当前未启用 hook，不影响现有工作流。**

---

## Agent-Browser — 无头浏览器

用于 AI agent 抓取网页、截图、提取结构化内容。

**硬边界：**
- 不接入 TG 自动发送
- 不接入 Market Radar 主链路
- 不用于生产环境
- 不爬取需要认证的页面
- 不提交截图/抓取结果到 COS/OSS

**Chrome 安装位置：**
`C:\Users\PC\.agent-browser\browsers\chrome-149.0.7827.54`

---

## 风险边界

- 本文件仅记录开发辅助工具
- 不创建 Windows 服务或开机自启
- 不读取 token/chat_id/SSH key
- 不修改事件情报系统代码
