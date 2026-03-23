import requests
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import datetime
import traceback
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==========================================
# 配置区一：SMTP 邮件告警参数
# ==========================================
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
AUTH_CODE = os.getenv("AUTH_CODE")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

# ==========================================
# 配置区二：Duckcoding 签到网络请求参数
# ==========================================
CHECKIN_URL = "https://duckcoding.com/api/user/checkin"
SESSION_COOKIE = os.getenv("SESSION_COOKIE")
NEW_API_USER = os.getenv("NEW_API_USER")

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "no-store",
    "cookie": f"session={SESSION_COOKIE}",
    "new-api-user": NEW_API_USER,
    "origin": "https://duckcoding.com",
    "referer": "https://duckcoding.com/console/personal",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}

def send_alert_email(subject, content):
    """底层通信模块：仅在被调用时触发告警"""
    message = MIMEText(content, 'plain', 'utf-8')
    message['From'] = formataddr((Header("签到监控服务", 'utf-8').encode(), SENDER_EMAIL))
    message['To'] = formataddr((Header("监控终端", 'utf-8').encode(), RECEIVER_EMAIL))
    message['Subject'] = Header(subject, 'utf-8')

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.login(SENDER_EMAIL, AUTH_CODE)
        server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], message.as_string())
        server.quit()
        print(f"[{datetime.datetime.now()}] 异常发生，告警邮件已送达。")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] 严重错误：告警邮件发送失败 - {e}")

def do_checkin():
    print(f"[{datetime.datetime.now()}] 开始执行 Duckcoding 签到任务...")
    try:
        # 发起 POST 请求
        response = requests.post(CHECKIN_URL, headers=HEADERS, timeout=15)
        
        # 1. 拦截 HTTP 协议层面的失败 (401, 403, 500 等)
        response.raise_for_status() 
        
        # 2. 尝试解析业务层面的 JSON 响应
        try:
            result = response.json()
        except ValueError:
            # 如果服务器返回的不是 JSON（比如 Nginx 的 502 HTML 页面），立刻判定为异常
            error_msg = f"服务器返回了非预期的格式 (非JSON)。\n状态码: {response.status_code}\n返回内容: {response.text[:200]}"
            print(f"[{datetime.datetime.now()}] 解析异常: {error_msg}")
            send_alert_email("🚨 签到异常：服务器返回格式错误", error_msg)
            return

        # 3. 拦截业务逻辑层面的失败 (状态码是200，但提示失败)
        # 注意：这里假设 JSON 中包含 code 或 msg 字段。你需要根据实际成功的 JSON 调整。
        # 如果你明确知道成功的 JSON 是什么，请修改这里的 if 条件。
        print(f"[{datetime.datetime.now()}] 响应内容: {result}")
        # 这是一个保守的防御逻辑：只要能正常解析到这步，且 HTTP 是 200，我们暂时认为它成功。
        # 如果你知道具体的失败特征（例如 result.get('code') != 200），应该在这里抛出异常并发送邮件。
        
        print(f"[{datetime.datetime.now()}] 签到成功，不触发邮件。")
        sys.exit(0) # 正常退出

    except requests.exceptions.RequestException as e:
        # 捕获所有网络层面的崩溃 (超时、DNS失败、401等)
        response_body = e.response.text if hasattr(e, 'response') and e.response is not None else "无响应体"
        error_msg = f"网络协议崩溃或凭证失效。\n错误详情：{e}\n服务器真实报文：{response_body}"
        print(f"[{datetime.datetime.now()}] 网络崩溃: {error_msg}")
        send_alert_email("🚨 签到异常：网络或权限被拒绝", error_msg)
        
    except Exception as e:
        # 捕获其他未知崩溃（例如内存溢出、环境配置错误）
        error_trace = traceback.format_exc()
        print(f"[{datetime.datetime.now()}] 未知崩溃:\n{error_trace}")
        send_alert_email("🚨 签到异常：脚本发生未知崩溃", error_trace)

if __name__ == "__main__":
    do_checkin()