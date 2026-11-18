"""Email notification service for BudgetBuddy.

Handles transactional HTML emails for critical financial events:
- Expense recorded / amount deducted
- Income added / money credited
- Savings goal created
- Savings goal deposit made / goal progress
- Budget alert / limit exceeded

Dispatched asynchronously and safely so API response times are never degraded.
"""

from __future__ import annotations

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from typing import Any

from app.core.config import settings

logger = logging.getLogger("budgetbuddy.email")


def _is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)


def _base_email_template(title: str, preheader: str, body_content: str) -> str:
    """Fintech dark theme HTML email template matching BudgetBuddy's aesthetic."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #070913;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #F8FAFC;
      -webkit-font-smoothing: antialiased;
    }}
    .container {{
      max-width: 560px;
      margin: 24px auto;
      background: #0E1326;
      border: 1px solid rgba(148, 163, 184, 0.16);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }}
    .header {{
      padding: 24px 28px;
      background: linear-gradient(180deg, rgba(16, 185, 129, 0.15) 0%, rgba(14, 19, 38, 0) 100%);
      border-bottom: 1px solid rgba(148, 163, 184, 0.12);
    }}
    .logo {{
      font-size: 20px;
      font-weight: 700;
      color: #10B981;
      letter-spacing: -0.02em;
    }}
    .content {{
      padding: 28px;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .badge-expense {{
      background: rgba(244, 63, 94, 0.15);
      color: #F43F5E;
      border: 1px solid rgba(244, 63, 94, 0.3);
    }}
    .badge-income {{
      background: rgba(16, 185, 129, 0.15);
      color: #10B981;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    .badge-goal {{
      background: rgba(6, 182, 212, 0.15);
      color: #06B6D4;
      border: 1px solid rgba(6, 182, 212, 0.3);
    }}
    .amount-hero {{
      font-size: 32px;
      font-weight: 700;
      margin: 14px 0 6px 0;
      letter-spacing: -0.03em;
    }}
    .amount-expense {{ color: #F43F5E; }}
    .amount-income {{ color: #10B981; }}
    .amount-goal {{ color: #06B6D4; }}
    .details-card {{
      background: #161D36;
      border: 1px solid rgba(148, 163, 184, 0.14);
      border-radius: 12px;
      padding: 16px 20px;
      margin: 20px 0;
    }}
    .row {{
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid rgba(148, 163, 184, 0.08);
      font-size: 14px;
    }}
    .row:last-child {{
      border-bottom: none;
    }}
    .row-label {{
      color: #94A3B8;
    }}
    .row-value {{
      font-weight: 600;
      color: #F8FAFC;
    }}
    .btn {{
      display: block;
      width: fit-content;
      margin: 24px auto 0;
      background: #10B981;
      color: #022C22;
      font-weight: 600;
      text-decoration: none;
      padding: 12px 24px;
      border-radius: 9999px;
      text-align: center;
      font-size: 14px;
    }}
    .footer {{
      padding: 20px 28px;
      background: #090D1C;
      border-top: 1px solid rgba(148, 163, 184, 0.1);
      text-align: center;
      font-size: 12px;
      color: #64748B;
    }}
  </style>
</head>
<body>
  <div style="display:none;font-size:1px;color:#333;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
    {preheader}
  </div>
  <div class="container">
    <div class="header">
      <div class="logo">⚡ BudgetBuddy</div>
    </div>
    <div class="content">
      {body_content}
    </div>
    <div class="footer">
      This is an automated notification from BudgetBuddy for your personal account.<br>
      Protecting your financial wellness every step of the way.
    </div>
  </div>
</body>
</html>"""


def _send_smtp_sync(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Synchronous SMTP worker intended to run in a background thread."""
    if not _is_smtp_configured():
        logger.warning(
            "[EMAIL NOTICE] SMTP not configured. Cannot send email to %s (Subject: %s).",
            to_email,
            subject,
        )
        return False

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "no-reply@budgetbuddy.app"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"BudgetBuddy <{from_email}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12)
            if settings.SMTP_USE_TLS:
                server.starttls()

        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info("Successfully sent email to %s with subject '%s'", to_email, subject)
        return True
    except Exception as exc:
        logger.warning("Failed to deliver email to %s: %s", to_email, exc)
        return False


async def send_email_async(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    """Fire and forget email dispatch offloaded to a background thread."""
    if not to_email:
        return
    try:
        await asyncio.to_thread(_send_smtp_sync, to_email, subject, html_body, text_body)
    except Exception as exc:
        logger.warning("Error scheduling async email: %s", exc)


async def send_verification_code(to_email: str, code: str) -> bool:
    """Send a 6-digit verification code via email.

    Returns True if sent (or logged in simulation), False on delivery error.
    """
    subject = "Your BudgetBuddy Verification Code"
    preheader = f"Your verification code is {code}. It expires in 10 minutes."

    html_content = f"""
      <span class="badge badge-goal">Email Verification</span>
      <div class="amount-hero amount-goal">{code}</div>
      <p style="margin: 0 0 16px 0; color: #94A3B8; font-size: 15px;">
        Use this code to verify your email address change. This code expires in 10 minutes.
      </p>
      <div class="details-card">
        <table style="width: 100%; border-collapse: collapse;">
          <tr>
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Verification Code</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px; letter-spacing: 0.2em;">{code}</td>
          </tr>
        </table>
      </div>
    """

    text_body = f"""Your BudgetBuddy Verification Code

Code: {code}
Expires in: 10 minutes

If you didn't request this, please ignore this email.
"""
    if not _is_smtp_configured():
        logger.warning("[SMTP UNCONFIGURED] Cannot send verification code to %s: SMTP is not configured.", to_email)
        return False

    try:
        sent = await asyncio.to_thread(
            _send_smtp_sync,
            to_email,
            subject,
            _base_email_template(subject, preheader, html_content),
            text_body,
        )
        return bool(sent)
    except Exception as exc:
        logger.warning("Failed to dispatch verification code email to %s: %s", to_email, exc)
        return False


def dispatch_email_in_background(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    """Non-blocking background launcher that will never block callers or fail requests."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_email_async(to_email, subject, html_body, text_body))
    except RuntimeError:
        # No running event loop, spawn thread
        import threading
        t = threading.Thread(
            target=_send_smtp_sync,
            args=(to_email, subject, html_body, text_body),
            daemon=True,
        )
        t.start()


# ---------------------------------------------------------------------------
# High-level Notification Dispatchers
# ---------------------------------------------------------------------------
def notify_expense_created(
    user_email: str,
    user_name: str,
    title: str,
    amount: Any,
    category: str,
    date_str: str,
    payment_method: str = "cash",
) -> None:
    """Send alert when money is deducted / spent."""
    clean_amt = f"₹{float(amount):,.2f}"
    clean_cat = category.replace("_", " ").title()
    subject = f"💸 Expense Alert: {clean_amt} spent on {clean_cat}"
    preheader = f"You recorded an expense of {clean_amt} for '{title}' on {date_str}."

    html_content = f"""
      <span class="badge badge-expense">Money Deducted</span>
      <div class="amount-hero amount-expense">-{clean_amt}</div>
      <p style="margin: 0 0 16px 0; color: #94A3B8; font-size: 15px;">
        Hi {user_name}, you logged a new expense in BudgetBuddy.
      </p>

      <div class="details-card">
        <table style="width: 100%; border-collapse: collapse;">
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Title</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{title}</td>
          </tr>
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Category</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{clean_cat}</td>
          </tr>
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Payment Method</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{payment_method.upper()}</td>
          </tr>
          <tr>
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Date</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{date_str}</td>
          </tr>
        </table>
      </div>

      <a href="https://budgetbuddy-student.vercel.app/analytics" class="btn">View Analytics & Budget</a>
    """

    text_body = f"""Hi {user_name},

Expense Alert: Money Deducted
Amount: -{clean_amt}
Title: {title}
Category: {clean_cat}
Payment Method: {payment_method.upper()}
Date: {date_str}

Check your updated spending trends at:
https://budgetbuddy-student.vercel.app/analytics
"""
    dispatch_email_in_background(
        user_email,
        subject,
        _base_email_template(subject, preheader, html_content),
        text_body,
    )


def notify_income_created(
    user_email: str,
    user_name: str,
    title: str,
    amount: Any,
    source_type: str,
    date_str: str,
) -> None:
    """Send alert when new money / income is credited."""
    clean_amt = f"₹{float(amount):,.2f}"
    clean_source = source_type.replace("_", " ").title()
    subject = f"💰 Income Credited: {clean_amt} added ({clean_source})"
    preheader = f"Great news! {clean_amt} was credited to your account from '{title}'."

    html_content = f"""
      <span class="badge badge-income">Money Credited</span>
      <div class="amount-hero amount-income">+{clean_amt}</div>
      <p style="margin: 0 0 16px 0; color: #94A3B8; font-size: 15px;">
        Hi {user_name}, new funds have been added to your budget.
      </p>

      <div class="details-card">
        <table style="width: 100%; border-collapse: collapse;">
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Source</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{clean_source}</td>
          </tr>
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Description</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{title}</td>
          </tr>
          <tr>
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Date</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{date_str}</td>
          </tr>
        </table>
      </div>

      <a href="https://budgetbuddy-student.vercel.app/dashboard" class="btn">View Dashboard</a>
    """

    text_body = f"""Hi {user_name},

Income Alert: Money Credited!
Amount: +{clean_amt}
Source: {clean_source}
Title: {title}
Date: {date_str}

Check your updated balance at:
https://budgetbuddy-student.vercel.app/dashboard
"""
    dispatch_email_in_background(
        user_email,
        subject,
        _base_email_template(subject, preheader, html_content),
        text_body,
    )


def notify_goal_created(
    user_email: str,
    user_name: str,
    title: str,
    target_amount: Any,
    priority: str,
    target_date_str: str | None,
) -> None:
    """Send alert when a new savings goal is set."""
    clean_target = f"₹{float(target_amount):,.2f}"
    deadline = target_date_str or "No deadline"
    subject = f"🎯 New Savings Goal Set: {title}"
    preheader = f"You set a new savings target of {clean_target} for '{title}'."

    html_content = f"""
      <span class="badge badge-goal">New Goal Created</span>
      <div class="amount-hero amount-goal">{clean_target}</div>
      <p style="margin: 0 0 16px 0; color: #94A3B8; font-size: 15px;">
        Hi {user_name}, you just set a new savings target for <strong>{title}</strong>!
      </p>

      <div class="details-card">
        <table style="width: 100%; border-collapse: collapse;">
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Goal Name</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{title}</td>
          </tr>
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Target Amount</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{clean_target}</td>
          </tr>
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Priority</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{priority.upper()}</td>
          </tr>
          <tr>
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Target Deadline</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{deadline}</td>
          </tr>
        </table>
      </div>

      <a href="https://budgetbuddy-student.vercel.app/goals" class="btn">Track Your Goal</a>
    """

    text_body = f"""Hi {user_name},

New Savings Goal Created!
Goal: {title}
Target Amount: {clean_target}
Priority: {priority.upper()}
Target Deadline: {deadline}

Track your progress:
https://budgetbuddy-student.vercel.app/goals
"""
    dispatch_email_in_background(
        user_email,
        subject,
        _base_email_template(subject, preheader, html_content),
        text_body,
    )


def notify_goal_deposit(
    user_email: str,
    user_name: str,
    title: str,
    deposit_amount: Any,
    current_amount: Any,
    target_amount: Any,
    is_completed: bool = False,
) -> None:
    """Send alert when a deposit is added to a savings goal."""
    clean_dep = f"₹{float(deposit_amount):,.2f}"
    clean_cur = f"₹{float(current_amount):,.2f}"
    clean_tgt = f"₹{float(target_amount):,.2f}"
    pct = round((float(current_amount) / max(float(target_amount), 1)) * 100, 1)

    if is_completed:
        subject = f"🎉 Goal Reached: '{title}' is 100% Completed!"
        badge = '<span class="badge badge-income">Goal Achieved!</span>'
        preheader = f"Congratulations! You reached your goal of {clean_tgt} for {title}!"
    else:
        subject = f"🌱 Goal Progress: {clean_dep} deposited into {title}"
        badge = '<span class="badge badge-goal">Deposit Recorded</span>'
        preheader = f"You deposited {clean_dep} into '{title}'. Total progress: {pct}%."

    html_content = f"""
      {badge}
      <div class="amount-hero amount-goal">+{clean_dep}</div>
      <p style="margin: 0 0 16px 0; color: #94A3B8; font-size: 15px;">
        Hi {user_name}, you just added a deposit towards <strong>{title}</strong>.
      </p>

      <div class="details-card">
        <table style="width: 100%; border-collapse: collapse;">
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Goal Name</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{title}</td>
          </tr>
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Deposit Added</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #10B981; font-size: 14px;">+{clean_dep}</td>
          </tr>
          <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.1);">
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Total Saved</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #F8FAFC; font-size: 14px;">{clean_cur} / {clean_tgt}</td>
          </tr>
          <tr>
            <td style="padding: 8px 0; color: #94A3B8; font-size: 14px;">Progress</td>
            <td style="padding: 8px 0; text-align: right; font-weight: 600; color: #06B6D4; font-size: 14px;">{pct}%</td>
          </tr>
        </table>
      </div>

      <a href="https://budgetbuddy-student.vercel.app/goals" class="btn">View Goal Details</a>
    """

    text_body = f"""Hi {user_name},

Goal Deposit Recorded!
Goal: {title}
Deposit: +{clean_dep}
Total Saved: {clean_cur} of {clean_tgt} ({pct}%)

View your goals:
https://budgetbuddy-student.vercel.app/goals
"""
    dispatch_email_in_background(
        user_email,
        subject,
        _base_email_template(subject, preheader, html_content),
        text_body,
    )
