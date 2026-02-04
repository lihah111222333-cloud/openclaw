---
description: 在远程服务器上部署和配置 API 代理（支持 gpteamservices 和 hanbbq 双供应商切换）
---

# API 代理部署工作流

## 概述

此工作流用于在远程服务器上部署 Python API 代理，支持：

- **双供应商切换**：gpteamservices / hanbbq
- **请求格式转换**：自动转换为 hanbbq Responses API 格式
- **多线程并发**：支持并发请求处理
- **守护进程**：systemd 管理，开机自启

## 前置条件

- 远程服务器 IP: `192.168.5.16` (可根据实际情况修改)
- 已配置 SSH 免密登录

---

## 第一部分：部署代理脚本

### 1. 复制脚本到服务器

```bash
scp scripts/api-proxy.py root@192.168.5.16:/root/api-proxy.py
```

### 2. 创建 systemd 服务文件

// turbo

```bash
ssh root@192.168.5.16 'cat > /etc/systemd/system/api-proxy.service << EOF
[Unit]
Description=API Proxy Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -u /root/api-proxy.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF'
```

### 3. 启动服务

// turbo

```bash
ssh root@192.168.5.16 'systemctl daemon-reload && systemctl enable api-proxy && systemctl start api-proxy'
```

### 4. 验证服务状态

// turbo

```bash
ssh root@192.168.5.16 'systemctl status api-proxy --no-pager | head -6'
```

---

## 第二部分：配置 OpenClaw 使用代理

### 1. 修改 OpenClaw 环境变量

编辑服务器上的 `~/.openclaw/.env`：

```bash
ssh root@192.168.5.16 'cat >> ~/.openclaw/.env << EOF
OPENAI_API_KEY=sk-any-key
OPENAI_BASE_URL=http://127.0.0.1:4000/v1
EOF'
```

### 2. 重启 OpenClaw Gateway

```bash
ssh root@192.168.5.16 'systemctl --user restart openclaw-gateway'
```

---

## 供应商切换命令

| 操作                  | URL                                              |
| --------------------- | ------------------------------------------------ |
| 切换到 hanbbq         | `http://192.168.5.16:4000/switch/hanbbq`         |
| 切换到 gpteamservices | `http://192.168.5.16:4000/switch/gpteamservices` |
| 查看当前状态          | `http://192.168.5.16:4000/status`                |

## 查看日志

// turbo

```bash
ssh root@192.168.5.16 'tail -20 /var/log/api-proxy.log'
```

---

## 供应商说明

| 供应商         | Base URL                         | 特性                        |
| -------------- | -------------------------------- | --------------------------- |
| gpteamservices | `https://api.gpteamservices.com` | 标准 OpenAI 格式            |
| hanbbq         | `https://api.hanbbq.top`         | 需要 Responses API 格式转换 |

## 故障排除

### 403 错误

- 检查 API Key 是否正确
- 检查 hanbbq 是否需要重新生成 Key

### 连接超时

- 检查代理服务是否运行：`systemctl status api-proxy`
- 检查端口是否监听：`ss -tlnp | grep 4000`
