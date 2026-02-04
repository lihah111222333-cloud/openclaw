---
description: 在远程服务器上部署和配置 API 代理（支持 gpteamservices 和 hanbbq 双供应商切换）
---

# API 代理部署工作流

## 1. 复制脚本到服务器

```bash
scp scripts/api-proxy.py root@192.168.5.16:/root/api-proxy.py
```

## 2. 创建 systemd 服务文件

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

## 3. 启动服务

// turbo

```bash
ssh root@192.168.5.16 'systemctl daemon-reload && systemctl enable api-proxy && systemctl start api-proxy'
```

## 4. 验证服务状态

// turbo

```bash
ssh root@192.168.5.16 'systemctl status api-proxy --no-pager | head -6'
```

## 5. 测试端点

// turbo

```bash
curl -s http://192.168.5.16:4000/status
```

## 供应商切换命令

| 操作                  | URL                                              |
| --------------------- | ------------------------------------------------ |
| 切换到 hanbbq         | `http://192.168.5.16:4000/switch/hanbbq`         |
| 切换到 gpteamservices | `http://192.168.5.16:4000/switch/gpteamservices` |
| 查看当前状态          | `http://192.168.5.16:4000/status`                |

## 查看日志

```bash
ssh root@192.168.5.16 'tail -20 /var/log/api-proxy.log'
```
