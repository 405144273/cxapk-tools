#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cxapk.com 每日自动签到（GitHub Actions 版）
配置通过环境变量读取，敏感信息存放在 GitHub Secrets
"""

import os
import sys
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

# ==================== 从环境变量读取配置 ====================
# GitHub Secrets 中配置后，会自动注入为环境变量
COOKIE = os.environ.get('CXAPK_COOKIE', '')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.qq.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', '')

AJAX_URL = 'https://cxapk.com/wp-admin/admin-ajax.php'


def log(msg):
    """输出日志到 Actions 控制台"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def get_headers(cookie):
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': cookie,
        'Referer': 'https://cxapk.com/',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://cxapk.com'
    }


def check_login(cookie):
    """验证 Cookie 是否有效"""
    try:
        resp = requests.get('https://cxapk.com/user/balance', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': cookie
        }, timeout=20)
        return 'Hi！请登录' not in resp.text
    except Exception as e:
        log(f"检查登录状态异常: {e}")
        return False


def sign_in(cookie):
    """执行签到"""
    data = {'action': 'user_checkin'}
    resp = requests.post(AJAX_URL, headers=get_headers(cookie), data=data, timeout=20)
    try:
        return resp.json()
    except Exception:
        return {'raw': resp.text}


def send_failure_email(error_msg):
    """Cookie失效时发送提醒邮件"""
    if not all([SENDER_EMAIL, SMTP_PASSWORD, RECEIVER_EMAIL]):
        log("未配置邮件参数，跳过失败提醒")
        return

    subject = '【提醒】cxapk.com 签到失败 - Cookie已失效'
    body = f"""
    <h2>cxapk.com 每日签到失败提醒</h2>
    <p><strong>时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>失败原因：</strong>{error_msg}</p>
    <hr>
    <p>请重新登录 cxapk.com 获取新的 Cookie，然后更新 GitHub Secrets 中的 <code>CXAPK_COOKIE</code>。</p>
    <p>获取方法：登录后按 F12 → 网络 → 刷新 → 点第一条请求 → 请求标头 → 复制 Cookie 值</p>
    """

    msg = MIMEText(body, 'html', 'utf-8')
    msg['From'] = formataddr((str(Header('签到提醒', 'utf-8')), SENDER_EMAIL))
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = Header(subject, 'utf-8')

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], msg.as_string())
        server.quit()
        log(f"失败提醒邮件已发送至 {RECEIVER_EMAIL}")
    except Exception as e:
        log(f"发送提醒邮件失败: {e}")


def main():
    log("=" * 50)
    log("cxapk.com 每日自动签到开始")
    log("=" * 50)

    if not COOKIE:
        log("错误：未配置 CXAPK_COOKIE 环境变量")
        sys.exit(1)

    # 1. 验证登录态
    log("[1/2] 验证登录状态...")
    if not check_login(COOKIE):
        error_msg = "Cookie 已失效，无法登录"
        log(error_msg)
        send_failure_email(error_msg)
        sys.exit(1)
    log("登录状态有效")

    # 2. 执行签到
    log("[2/2] 执行签到...")
    result = sign_in(COOKIE)
    log(f"签到响应: {json.dumps(result, ensure_ascii=False)}")

    if isinstance(result, dict):
        if result.get('error'):
            error_msg = f"签到失败: {result.get('msg', '未知错误')}"
            log(error_msg)
            send_failure_email(error_msg)
            sys.exit(1)
        elif result.get('msg'):
            log(f"签到结果: {result['msg']}")
        else:
            log("签到已执行")

    log("签到流程结束")


if __name__ == '__main__':
    main()
