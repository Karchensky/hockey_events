from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Iterable
from loguru import logger


def _send(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    from_email: str,
    to_emails: Iterable[str],
    subject: str,
    body: str,
    use_tls: bool = True,
) -> None:
    if not to_emails:
        return
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if use_tls:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if username:
                    server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                if username:
                    server.login(username, password)
                server.send_message(msg)
    except Exception as exc:
        logger.error(f"Failed to send email: {exc}")


def send_summary(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    from_email: str,
    to_emails: Iterable[str],
    subject: str,
    body: str,
    use_tls: bool = True,
) -> None:
    _send(smtp_server, smtp_port, username, password, from_email, to_emails, subject, body, use_tls)


def send_personal(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    use_tls: bool = True,
) -> None:
    _send(smtp_server, smtp_port, username, password, from_email, [to_email], subject, body, use_tls)