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
LOGIN_URL = "https://duckcoding.com/api/user/login"
CHECKIN_URL = "https://duckcoding.com/api/user/checkin"
DUCK_EMAIL = os.getenv("DUCK_EMAIL")
DUCK_PASSWORD = os.getenv("DUCK_PASSWORD")
SESSION_COOKIE = os.getenv("SESSION_COOKIE")
NEW_API_USER = os.getenv("NEW_API_USER")

BASE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "no-store",
    "content-type": "application/json",
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

def login():
    """使用邮箱密码登录，获取 session cookie"""
    if not DUCK_EMAIL or not DUCK_PASSWORD:
        print(f"[{datetime.datetime.now()}] 未配置邮箱密码，尝试使用预设的 session cookie")
        return SESSION_COOKIE

    print(f"[{datetime.datetime.now()}] 开始登录...")
    login_headers = BASE_HEADERS.copy()
    login_headers["referer"] = "https://duckcoding.com/login"

    payload = {
        "username": DUCK_EMAIL,
        "password": DUCK_PASSWORD
    }

    try:
        response = requests.post(LOGIN_URL, json=payload, headers=login_headers, timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get('success'):
            # 从响应的 cookies 中获取 session
            session_cookie = response.cookies.get('session')
            if session_cookie:
                print(f"[{datetime.datetime.now()}] 登录成功，已获取 session")
                return session_cookie
            else:
                raise Exception("登录成功但未获取到 session cookie")
        else:
            raise Exception(f"登录失败: {result.get('message', '未知错误')}")

    except Exception as e:
        print(f"[{datetime.datetime.now()}] 登录异常: {e}")
        raise

def do_checkin():
    print(f"[{datetime.datetime.now()}] 开始执行 Duckcoding 签到任务...")

    session = None
    try:
        # 优先使用邮箱密码登录获取 session
        if DUCK_EMAIL and DUCK_PASSWORD:
            session = login()
        elif SESSION_COOKIE:
            print(f"[{datetime.datetime.now()}] 使用预设的 session cookie")
            session = SESSION_COOKIE
        else:
            raise Exception("既未配置邮箱密码，也未配置 session cookie")

        # 构建签到请求头
        checkin_headers = BASE_HEADERS.copy()
        checkin_headers["cookie"] = f"session={session}"
        checkin_headers["new-api-user"] = NEW_API_USER

        # 发起签到请求
        response = requests.post(CHECKIN_URL, headers=checkin_headers, timeout=15)
        response.raise_for_status()

        try:
            result = response.json()
        except ValueError:
            error_msg = f"服务器返回了非预期的格式 (非JSON)。\n状态码: {response.status_code}\n返回内容: {response.text[:200]}"
            print(f"[{datetime.datetime.now()}] 解析异常: {error_msg}")
            send_alert_email("🚨 签到异常：服务器返回格式错误", error_msg)
            return

        print(f"[{datetime.datetime.now()}] 响应内容: {result}")

        if result.get('success'):
            print(f"[{datetime.datetime.now()}] 签到成功，不触发邮件。")
            sys.exit(0)
        elif result.get('message') == '今日已签到':
            print(f"[{datetime.datetime.now()}] 今日已签到，不触发邮件。")
            sys.exit(0)
        else:
            # 可能是 session 过期，如果配置了邮箱密码则尝试重新登录
            if DUCK_EMAIL and DUCK_PASSWORD:
                print(f"[{datetime.datetime.now()}] 签到失败，可能 session 过期，尝试重新登录...")
                session = login()
                checkin_headers["cookie"] = f"session={session}"
                response = requests.post(CHECKIN_URL, headers=checkin_headers, timeout=15)
                response.raise_for_status()
                result = response.json()
                print(f"[{datetime.datetime.now()}] 重试后响应: {result}")

                if result.get('success'):
                    print(f"[{datetime.datetime.now()}] 重试签到成功。")
                    sys.exit(0)
                elif result.get('message') == '今日已签到':
                    print(f"[{datetime.datetime.now()}] 今日已签到，不触发邮件。")
                    sys.exit(0)
                else:
                    raise Exception(f"签到失败: {result.get('message', '未知错误')}")
            else:
                raise Exception(f"签到失败: {result.get('message', '未知错误')}")

    except requests.exceptions.RequestException as e:
        response_body = e.response.text if hasattr(e, 'response') and e.response is not None else "无响应体"
        error_msg = f"网络协议崩溃或凭证失效。\n错误详情：{e}\n服务器真实报文：{response_body}"
        print(f"[{datetime.datetime.now()}] 网络崩溃: {error_msg}")
        send_alert_email("🚨 签到异常：网络或权限被拒绝", error_msg)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[{datetime.datetime.now()}] 未知崩溃:\n{error_trace}")
        send_alert_email("🚨 签到异常：脚本发生未知崩溃", error_trace)

if __name__ == "__main__":
    do_checkin()
