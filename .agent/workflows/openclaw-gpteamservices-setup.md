---
description: OpenClaw 配置 GPTeamServices API 并完成前端中文化
---

# OpenClaw GPTeamServices 设置工作流

此工作流用于将 OpenClaw 配置为使用 GPTeamServices API 提供商，并完成前端 UI 的中文化。

## 前置条件

- OpenClaw 已安装并配置
- 有效的 GPTeamServices API Key
- pnpm 已安装

---

## 第一部分：GPTeamServices API 配置

### 1. 设置 API 环境变量

编辑 `~/.openclaw/.env` 文件：

```bash
cat >> ~/.openclaw/.env << 'EOF'
OPENAI_API_KEY=sk-你的API密钥
OPENAI_BASE_URL=https://api.gpteamservices.com/v1
EOF
```

### 2. 应用 "Nuke Patch" 重定向

如果环境变量无效，执行全局域名替换：

// turbo

```bash
# 后端依赖
find /usr/lib/node_modules/openclaw/node_modules -name '*.js' -exec grep -l 'api.openai.com' {} \; 2>/dev/null | xargs -I {} sed -i 's|api.openai.com|api.gpteamservices.com|g' {}

# dist 目录
find /usr/lib/node_modules/openclaw/dist -name '*.js' -exec grep -l 'api.openai.com' {} \; 2>/dev/null | xargs -I {} sed -i 's|api.openai.com|api.gpteamservices.com|g' {}
```

### 3. 验证 Patch 生效

// turbo

```bash
grep -c "gpteamservices" /usr/lib/node_modules/openclaw/node_modules/openai/client.js
```

### 4. 重启 Gateway

```bash
systemctl --user restart openclaw-gateway
```

---

## 第二部分：前端中文化

### 1. 进入项目目录

// turbo

```bash
cd /Users/mima0000/Desktop/wj/openclaw
```

### 2. 翻译 `chat.ts`

编辑 `ui/src/ui/views/chat.ts`，替换以下字符串：

| 英文                                      | 中文                                        |
| ----------------------------------------- | ------------------------------------------- |
| `"Send"`                                  | `"发送"`                                    |
| `"Queue"`                                 | `"排队"`                                    |
| `"Stop"`                                  | `"停止"`                                    |
| `"New session"`                           | `"新会话"`                                  |
| `"Loading chat…"`                         | `"加载中…"`                                 |
| `"Message"`                               | `"消息"`                                    |
| `"Compacting context..."`                 | `"正在压缩上下文..."`                       |
| `"Context compacted"`                     | `"上下文已压缩"`                            |
| `"New messages"`                          | `"新消息"`                                  |
| `"Queued"`                                | `"已排队"`                                  |
| `"Exit focus mode"` (title)               | `"退出专注模式"`                            |
| `"Message (↩ to send..."` placeholder     | `"消息 (↩ 发送, Shift+↩ 换行, 可粘贴图片)"` |
| `"Add a message or paste more images..."` | `"添加消息或粘贴更多图片..."`               |
| `"Connect to the gateway..."`             | `"连接到网关后开始聊天..."`                 |
| `"Image"`                                 | `"图片"`                                    |
| `"Remove attachment"`                     | `"移除附件"`                                |
| `"Remove queued message"`                 | `"移除排队消息"`                            |

### 3. 翻译 `app-render.ts`

编辑 `ui/src/ui/app-render.ts`，替换：

| 英文                        | 中文                    |
| --------------------------- | ----------------------- |
| `"Expand sidebar"`          | `"展开侧边栏"`          |
| `"Collapse sidebar"`        | `"折叠侧边栏"`          |
| `"Gateway Dashboard"`       | `"网关控制台"`          |
| `"Health"`                  | `"状态"`                |
| `"OK"`                      | `"正常"`                |
| `"Offline"`                 | `"离线"`                |
| `"Resources"`               | `"资源"`                |
| `"Docs"`                    | `"文档"`                |
| `"Docs (opens in new tab)"` | `"文档 (新标签页打开)"` |

### 4. 翻译通用字符串

多个文件中的通用字符串：

| 英文                       | 中文              | 涉及文件                                               |
| -------------------------- | ----------------- | ------------------------------------------------------ |
| `"Loading…"`               | `"加载中…"`       | config.ts, agents.ts, skills.ts, instances.ts, logs.ts |
| `"Refresh"`                | `"刷新"`          | 同上                                                   |
| `"Reload"`                 | `"重载"`          | config.ts                                              |
| `"Loading schema…"`        | `"加载配置模式…"` | config.ts                                              |
| `"Loading config schema…"` | `"加载配置模式…"` | channels.config.ts                                     |
| `"Save"`                   | `"保存"`          | 多处                                                   |

### 5. 构建 UI

// turbo

```bash
pnpm run ui:build
```

### 6. 部署（可选）

如果在远程服务器上：

```bash
# 打包
cd /Users/mima0000/Desktop/wj/openclaw
zip -r openclaw-dist.zip dist/

# 复制到服务器
scp openclaw-dist.zip root@<SERVER_IP>:/tmp/

# 在服务器上
cd /usr/lib/node_modules/openclaw
rm -rf dist
unzip /tmp/openclaw-dist.zip
systemctl --user restart openclaw-gateway
```

---

## 验证

1. 访问 Control UI: `http://localhost:18789/?token=<TOKEN>`
2. 检查：
   - 导航菜单显示中文
   - 聊天界面按钮显示中文
   - 加载状态显示中文
