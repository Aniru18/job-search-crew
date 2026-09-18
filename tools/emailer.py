"""
tools/emailer.py
Sends the final job digest email.

Written as a swappable interface: GmailSMTPSender works today with zero
extra services. If this is ever deployed for other people to use at scale,
swap in a ResendSender/SendGridSender without touching the rest of the app --
just change get_email_sender().
"""
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD


class EmailSender(ABC):
    @abstractmethod
    def send(self, to_email: str, subject: str, html_body: str) -> None:
        ...


class GmailSMTPSender(EmailSender):
    def send(self, to_email: str, subject: str, html_body: str) -> None:
        if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
            raise RuntimeError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set in environment.")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)


def get_email_sender() -> EmailSender:
    """Single place to swap the email provider later."""
    return GmailSMTPSender()


def build_email_html(jobs: List[Dict]) -> str:
    rows = ""
    for job in jobs:
        rows += f"""
        <tr>
          <td style="padding:16px;border-bottom:1px solid #e5e5e5;">
            <h3 style="margin:0 0 4px 0;font-size:16px;">{job.get('title', '')}</h3>
            <p style="margin:0 0 8px 0;color:#555;font-size:14px;">
              {job.get('company', '')} &middot; {job.get('location', '')}
            </p>
            <p style="margin:0 0 12px 0;font-size:14px;line-height:1.5;">
              {job.get('summary', '')}
            </p>
            <a href="{job.get('apply_url', '#')}"
               style="display:inline-block;padding:8px 16px;background:#2563eb;
                      color:#ffffff;text-decoration:none;border-radius:6px;font-size:14px;">
              Apply now
            </a>
          </td>
        </tr>
        """

    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;background:#f5f5f5;padding:24px;">
        <table style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;">
          <tr>
            <td style="padding:20px;background:#111827;color:#ffffff;">
              <h2 style="margin:0;font-size:18px;">Your top {len(jobs)} job matches today</h2>
            </td>
          </tr>
          {rows}
        </table>
      </body>
    </html>
    """


def send_job_digest_email(to_email: str, jobs: List[Dict]) -> None:
    sender = get_email_sender()
    html = build_email_html(jobs)
    subject = f"Your {len(jobs)} matched job(s) for today"
    sender.send(to_email, subject, html)
