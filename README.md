# Auto Check-in

Duckcoding 自动签到脚本，支持异常邮件告警。部署在服务器后可通过定时任务实现每日签到。

## 📋 功能特点

* **自动登录**：使用账号密码自动登录获取 Session，无需手动更新 Cookie
* **Session 过期重试**：签到失败时自动重新登录并重试
* **API 模拟**：直接调用后端 API 接口，无需浏览器，资源占用极低
* **邮件告警**：签到失败时自动发送邮件通知
* **多层异常检测**：
  * HTTP 层：401/403/500 等状态码
  * 业务层：非 JSON 响应格式
  * 网络层：超时、DNS 失败
  * 未知异常：捕获所有未预期错误
* **日志记录**：带时间戳的运行日志，便于排查问题

## 🛠️ 环境依赖

* **Python 3.x**
* **Python 库**：`requests`、`python-dotenv`

### 安装依赖
```bash
pip3 install requests python-dotenv
```

## ⚙️ 配置说明

1. 复制配置模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填写以下配置：

### SMTP 邮件告警配置
| 配置项 | 说明 |
|--------|------|
| `SMTP_SERVER` | SMTP 服务器地址（如 163 邮箱：smtp.163.com） |
| `SMTP_PORT` | SMTP 端口（通常为 465） |
| `SENDER_EMAIL` | 发件邮箱地址（建议使用 163 邮箱） |
| `AUTH_CODE` | 邮箱 SMTP 授权码（非登录密码） |
| `RECEIVER_EMAIL` | 接收告警的邮箱地址 |

### Duckcoding 签到配置
| 配置项 | 说明 |
|--------|------|
| `DUCK_EMAIL` | Duckcoding 登录邮箱 |
| `DUCK_PASSWORD` | Duckcoding 登录密码 |
| `NEW_API_USER` | 用户 ID（可在浏览器开发者工具中查看） |

**获取 163 授权码方法**：登录 163 邮箱 → 设置 → POP3/SMTP/IMAP → 开启 SMTP 服务 → 生成授权码。

## 🚀 使用方法

```bash
python3 duck_checkin.py
```

## ⏰ 定时任务设置

1. 确认解释器路径：
```bash
which python3
```

2. 编辑 Crontab：
```bash
crontab -e
```

3. 写入定时规则：
```bash
30 07 * * * cd /home/user/projects/daily_checkin && /usr/bin/python3 duck_checkin.py >> /home/user/projects/daily_checkin/checkin.log 2>&1
```

- `30 07 * * *`：每天 07:30 执行
- `checkin.log`：将标准输出追加到日志文件
- `2>&1`：将错误信息（如有报错）也重定向到日志文件中，方便排查

4. 确认任务已添加：
```bash
crontab -l
```

## ⚠️ 安全提示

- 请妥善保管 `.env` 文件，不要将其上传到公共仓库
- `.env` 文件已加入 `.gitignore`，不会被提交到 Git

## 📝 更新日志

### v2.0
- 新增自动登录功能，使用账号密码自动获取 Session
- 新增 Session 过期时自动重新登录并重试
- 支持"今日已签到"场景，不会重复告警
- 改用 `.env` 环境变量配置，更加安全方便

### v1.0
- 基础签到功能
- 邮件告警功能
