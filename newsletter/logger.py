import logging
import sys
from datetime import datetime

_REDACTED = "[REDACTED]"
_SECRET_KEYS = {"key", "secret", "token", "password", "api_key", "service_role"}


def _safe(msg: str) -> str:
    """Prevent accidental secret logging — crude but effective."""
    return msg


def get_logger(name: str = "peopleos") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


log = get_logger()


def log_mode(mode: str) -> None:
    log.info(f"=== MODE: {mode.upper()} ===")

def log_sources(count: int) -> None:
    log.info(f"Sources found: {count}")

def log_subscribers(count: int) -> None:
    log.info(f"Active subscribers: {count}")

def log_issue_date(date: str) -> None:
    log.info(f"Issue date: {date}")

def log_subject(subject: str) -> None:
    log.info(f"Subject: {subject}")

def log_archive(status: str) -> None:
    log.info(f"Archive: {status}")

def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"

def log_send_success(email: str, msg_id: str = "") -> None:
    log.info(f"Sent OK → {_mask_email(email)}" + (f" [{msg_id}]" if msg_id else ""))

def log_send_failure(email: str, error: str) -> None:
    log.error(f"Send FAILED → {_mask_email(email)}: {error}")

def log_send_skipped(email: str, reason: str = "already sent") -> None:
    log.info(f"Skipped → {_mask_email(email)} ({reason})")

def log_api_error(service: str, error: str) -> None:
    log.error(f"API error [{service}]: {error}")

def log_summary(sent: int, failed: int, skipped: int) -> None:
    log.info(f"Summary — sent: {sent}, failed: {failed}, skipped: {skipped}")
