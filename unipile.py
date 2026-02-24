#!/usr/bin/env python3
"""
Unipile Comprehensive MCP Server (94 tools)

A comprehensive MCP server for the full Unipile API covering:
- Account management (list, get, connect, delete, reconnect, resync, restart, checkpoints)
- Cross-platform messaging (LinkedIn, WhatsApp, Instagram, Telegram) with cross-chat search
- Attendee management (list, get, pictures, chats, reactions)
- Email (Gmail + Outlook unified, with open/click tracking)
- Calendar (Google + Microsoft unified)
- LinkedIn search, profiles, users (followers, following, comments, reactions)
- LinkedIn connections, InMail, posts & content
- LinkedIn jobs & recruiter (hiring projects, applicants, actions)
- Webhooks (real-time events for all actions)
- Advanced LinkedIn operations
"""

import os
import sys
import json
import base64
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("unipile")

mcp = FastMCP("unipile")


class UnipileClient:
    """HTTP client for Unipile API — works across all connected platforms."""

    def __init__(self):
        self.base_url = os.getenv("UNIPILE_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("UNIPILE_API_KEY", "")
        self.linkedin_account_id = os.getenv("UNIPILE_LINKEDIN_ACCOUNT_ID", "")
        self.email_account_id = os.getenv("UNIPILE_EMAIL_ACCOUNT_ID", "")

        if not self.base_url or not self.api_key:
            raise ValueError("UNIPILE_BASE_URL and UNIPILE_API_KEY must be set")

        self.headers = {
            "X-API-KEY": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        account_id: Optional[str] = None,
        expect_binary: bool = False
    ) -> dict:
        """Make an HTTP request to the Unipile API.

        account_id is only injected when explicitly passed — NOT by default.
        This allows messaging tools to work across all platforms.

        When expect_binary is True, returns {content_type, size_bytes, data_base64}
        instead of parsing JSON. Used for attachments, resumes, etc.
        """
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}

        # Only inject account_id if explicitly provided
        if account_id and "account_id" not in params:
            params["account_id"] = account_id

        if json_data is not None and account_id:
            if "account_id" not in json_data:
                json_data["account_id"] = account_id

        logger.info(f"Request: {method} {url}")

        async with httpx.AsyncClient(timeout=60.0) as http:
            response = await http.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data
            )

            logger.info(f"Response status: {response.status_code}")

            if response.status_code >= 400:
                error_text = response.text
                logger.error(f"API Error: {error_text}")
                return {"error": error_text, "status_code": response.status_code}

            if expect_binary:
                content_type = response.headers.get("content-type", "application/octet-stream")
                data = base64.b64encode(response.content).decode("ascii")
                return {
                    "content_type": content_type,
                    "size_bytes": len(response.content),
                    "data_base64": data
                }

            try:
                return response.json()
            except json.JSONDecodeError:
                return {"raw_response": response.text}


client = UnipileClient()


# =============================================================================
# ACCOUNT MANAGEMENT (10 tools)
# =============================================================================

@mcp.tool()
async def list_accounts() -> dict:
    """List all connected accounts (LinkedIn, WhatsApp, Email, etc.).

    Returns account IDs, types, status, and connection details for
    all platforms linked to your Unipile integration.
    """
    return await client.request("GET", "/accounts", params={})


@mcp.tool()
async def get_my_profile() -> dict:
    """Get the authenticated user's LinkedIn profile.

    Returns profile data including name, headline, summary,
    experience, education, and skills.
    """
    return await client.request("GET", "/users/me",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def delete_account(account_id: str) -> dict:
    """Delete a connected account from Unipile.

    Args:
        account_id: The account ID to delete
    """
    return await client.request("DELETE", f"/accounts/{account_id}")


@mcp.tool()
async def reconnect_account(
    account_id: str,
    google_scopes: Optional[str] = None
) -> dict:
    """Reconnect a disconnected account via hosted authentication.

    Returns a URL that the user must open in a browser to re-authorize.

    Args:
        account_id: The account ID to reconnect
        google_scopes: Optional comma-separated Google OAuth scope URLs (max 6).
                       Example: "https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/calendar"
    """
    body = {
        "type": "reconnect",
        "reconnect_account": account_id,
        "expiresOn": "2099-12-31T23:59:59.999Z",
        "api_url": client.base_url.rsplit("/api/", 1)[0],
    }
    if google_scopes:
        body["google_scopes"] = google_scopes
    return await client.request("POST", "/hosted/accounts/link", json_data=body)


@mcp.tool()
async def resync_account(account_id: str) -> dict:
    """Force a full resync of an account's data.

    Args:
        account_id: The account ID to resync
    """
    return await client.request("GET", f"/accounts/{account_id}/resync")


@mcp.tool()
async def get_account(account_id: str) -> dict:
    """Get details of a single connected account.

    Args:
        account_id: The account ID to retrieve
    """
    return await client.request("GET", f"/accounts/{account_id}")


@mcp.tool()
async def connect_account(
    provider: str,
    username: str,
    password: str,
    imap_host: Optional[str] = None,
    imap_port: Optional[int] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None
) -> dict:
    """Connect a new account using native authentication (username/password).

    Args:
        provider: Provider name (e.g. 'LINKEDIN', 'WHATSAPP', 'TELEGRAM', 'CUSTOM_IMAP')
        username: Account username or email
        password: Account password or app-specific password
        imap_host: IMAP server host (for CUSTOM_IMAP provider)
        imap_port: IMAP server port (for CUSTOM_IMAP provider)
        smtp_host: SMTP server host (for CUSTOM_IMAP provider)
        smtp_port: SMTP server port (for CUSTOM_IMAP provider)
    """
    body = {
        "provider": provider,
        "username": username,
        "password": password
    }
    if imap_host:
        body["imap_host"] = imap_host
    if imap_port:
        body["imap_port"] = imap_port
    if smtp_host:
        body["smtp_host"] = smtp_host
    if smtp_port:
        body["smtp_port"] = smtp_port
    return await client.request("POST", "/accounts", json_data=body)


@mcp.tool()
async def solve_checkpoint(
    account_id: str,
    code: str,
    provider: str
) -> dict:
    """Solve a 2FA/checkpoint challenge during account connection.

    Args:
        account_id: The account ID requiring checkpoint
        code: The verification/2FA code
        provider: Provider name (e.g. 'LINKEDIN', 'WHATSAPP')
    """
    body = {
        "account_id": account_id,
        "code": code,
        "provider": provider
    }
    return await client.request("POST", "/accounts/checkpoint", json_data=body)


@mcp.tool()
async def resend_checkpoint(
    account_id: str,
    provider: str
) -> dict:
    """Resend a checkpoint/2FA verification code.

    Args:
        account_id: The account ID requiring checkpoint
        provider: Provider name (e.g. 'LINKEDIN', 'WHATSAPP')
    """
    body = {
        "account_id": account_id,
        "provider": provider
    }
    return await client.request("POST", "/accounts/checkpoint/resend", json_data=body)


@mcp.tool()
async def restart_account(account_id: str) -> dict:
    """Restart sync processes for an account.

    Args:
        account_id: The account ID to restart
    """
    return await client.request("POST", f"/accounts/{account_id}/restart")


# =============================================================================
# UNIFIED MESSAGING (14 tools — works across LinkedIn, WhatsApp, Email, etc.)
# =============================================================================

@mcp.tool()
async def list_chats(
    limit: int = 50,
    cursor: Optional[str] = None,
    unread_only: bool = False,
    account_id: Optional[str] = None
) -> dict:
    """List message conversations across ALL connected platforms.

    Returns chats from LinkedIn, WhatsApp, Email, and any other connected
    accounts. Use account_id to filter to a specific platform.

    Args:
        limit: Max results per page (default 50)
        cursor: Pagination cursor from previous response
        unread_only: If True, only return chats with unread messages
        account_id: Optional - filter to specific account (e.g. WhatsApp account ID).
                    If omitted, returns chats from ALL connected accounts.
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    if unread_only:
        params["unread"] = "true"

    return await client.request("GET", "/chats", params=params,
                                account_id=account_id)


@mcp.tool()
async def get_chat(chat_id: str) -> dict:
    """Get details for a specific chat conversation.

    Args:
        chat_id: The chat/conversation ID
    """
    return await client.request("GET", f"/chats/{chat_id}")


@mcp.tool()
async def sync_chat(chat_id: str) -> dict:
    """Sync a chat to get the latest messages and state.

    Args:
        chat_id: The chat/conversation ID to sync
    """
    return await client.request("GET", f"/chats/{chat_id}/sync")


@mcp.tool()
async def update_chat(
    chat_id: str,
    archived: Optional[bool] = None,
    muted: Optional[bool] = None,
    read: Optional[bool] = None
) -> dict:
    """Update chat settings (archive, mute, mark read/unread).

    Args:
        chat_id: The chat/conversation ID
        archived: Set to True to archive, False to unarchive
        muted: Set to True to mute notifications
        read: Set to True to mark as read
    """
    body = {}
    if archived is not None:
        body["archived"] = archived
    if muted is not None:
        body["muted"] = muted
    if read is not None:
        body["read"] = read

    return await client.request("PATCH", f"/chats/{chat_id}", json_data=body)


@mcp.tool()
async def list_chat_attendees(chat_id: str) -> dict:
    """List participants in a specific chat.

    Args:
        chat_id: The chat/conversation ID
    """
    return await client.request("GET", f"/chats/{chat_id}/attendees")


@mcp.tool()
async def get_chat_messages(
    chat_id: str,
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """Get messages from a specific chat (works for any platform).

    Args:
        chat_id: The chat/conversation ID (from list_chats)
        limit: Max messages per page (default 50)
        cursor: Pagination cursor from previous response
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", f"/chats/{chat_id}/messages", params=params)


@mcp.tool()
async def get_message(message_id: str) -> dict:
    """Get a specific message by ID.

    Args:
        message_id: The message ID
    """
    return await client.request("GET", f"/messages/{message_id}")


@mcp.tool()
async def send_message(chat_id: str, text: str) -> dict:
    """Send a message in an existing chat (works for any platform).

    Use this for ongoing conversations on LinkedIn, WhatsApp, or any
    connected platform. The platform is determined by the chat_id.

    Args:
        chat_id: The chat/conversation ID (from list_chats)
        text: The message content to send
    """
    body = {"text": text}
    return await client.request("POST", f"/chats/{chat_id}/messages", json_data=body)


@mcp.tool()
async def forward_message(message_id: str, chat_id: str) -> dict:
    """Forward a message to another chat.

    Args:
        message_id: The message ID to forward
        chat_id: The target chat ID to forward to
    """
    body = {"chat_id": chat_id}
    return await client.request("POST", f"/messages/{message_id}/forward", json_data=body)


@mcp.tool()
async def get_message_attachment(message_id: str) -> dict:
    """Download a message attachment (returns base64-encoded binary).

    Args:
        message_id: The message ID containing the attachment

    Returns:
        {content_type, size_bytes, data_base64}
    """
    return await client.request("GET", f"/messages/{message_id}/attachment",
                                expect_binary=True)


@mcp.tool()
async def start_chat(
    attendees_ids: list[str],
    text: str,
    account_id: Optional[str] = None
) -> dict:
    """Start a new conversation on any connected platform.

    For LinkedIn: pass LinkedIn provider IDs.
    For WhatsApp: pass phone numbers (with country code, e.g. "919876543210").

    Args:
        attendees_ids: List of provider IDs or phone numbers
        text: The initial message content
        account_id: Optional - specify which account to use.
                    Defaults to LinkedIn if not specified.
    """
    body = {
        "attendees_ids": attendees_ids,
        "text": text
    }

    acc = account_id or client.linkedin_account_id
    return await client.request("POST", "/chats", json_data=body, account_id=acc)


@mcp.tool()
async def list_all_messages(
    limit: int = 50,
    cursor: Optional[str] = None,
    before: Optional[str] = None,
    after: Optional[str] = None,
    sender_id: Optional[str] = None,
    account_id: Optional[str] = None
) -> dict:
    """List messages across all chats (cross-chat search).

    Args:
        limit: Max results (default 50)
        cursor: Pagination cursor
        before: Only messages before this ISO8601 datetime
        after: Only messages after this ISO8601 datetime
        sender_id: Filter by sender provider ID
        account_id: Optional - filter to specific account
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    if before:
        params["before"] = before
    if after:
        params["after"] = after
    if sender_id:
        params["sender_id"] = sender_id
    return await client.request("GET", "/messages", params=params,
                                account_id=account_id)


@mcp.tool()
async def delete_chat(chat_id: str) -> dict:
    """Delete a chat conversation.

    Args:
        chat_id: The chat ID to delete
    """
    return await client.request("DELETE", f"/chats/{chat_id}")


@mcp.tool()
async def delete_message(message_id: str) -> dict:
    """Delete a specific message.

    Args:
        message_id: The message ID to delete
    """
    return await client.request("DELETE", f"/messages/{message_id}")


# =============================================================================
# ATTENDEES (6 tools)
# =============================================================================

@mcp.tool()
async def list_attendees(
    limit: int = 50,
    cursor: Optional[str] = None,
    account_id: Optional[str] = None
) -> dict:
    """List all known chat attendees (contacts) across connected platforms.

    Args:
        limit: Max results per page (1-250, default 50)
        cursor: Pagination cursor
        account_id: Optional - filter to specific account
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", "/chat_attendees", params=params,
                                account_id=account_id)


@mcp.tool()
async def list_messages_by_attendee(
    sender_id: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    account_id: Optional[str] = None,
    before: Optional[str] = None,
    after: Optional[str] = None
) -> dict:
    """List all messages from a specific attendee.

    Args:
        sender_id: The attendee's Unipile ID or provider_id
        limit: Max results per page (1-250, default 50)
        cursor: Pagination cursor
        account_id: Optional - filter to specific account
        before: Only messages before this ISO8601 datetime
        after: Only messages after this ISO8601 datetime
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    if before:
        params["before"] = before
    if after:
        params["after"] = after

    return await client.request("GET", f"/chat_attendees/{sender_id}/messages",
                                params=params, account_id=account_id)


@mcp.tool()
async def get_attendee(attendee_id: str) -> dict:
    """Get details of a single chat attendee.

    Args:
        attendee_id: The attendee ID
    """
    return await client.request("GET", f"/chat_attendees/{attendee_id}")


@mcp.tool()
async def get_attendee_picture(attendee_id: str) -> dict:
    """Get an attendee's profile picture (returns base64-encoded binary).

    Args:
        attendee_id: The attendee ID

    Returns:
        {content_type, size_bytes, data_base64}
    """
    return await client.request("GET", f"/chat_attendees/{attendee_id}/picture",
                                expect_binary=True)


@mcp.tool()
async def list_chats_by_attendee(
    attendee_id: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    account_id: Optional[str] = None
) -> dict:
    """List all chats that a specific attendee is part of.

    Args:
        attendee_id: The attendee ID
        limit: Max results (default 50)
        cursor: Pagination cursor
        account_id: Optional - filter to specific account
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await client.request("GET", f"/chat_attendees/{attendee_id}/chats",
                                params=params, account_id=account_id)


@mcp.tool()
async def add_message_reaction(
    message_id: str,
    reaction: str
) -> dict:
    """Add a reaction to a message.

    Args:
        message_id: The message ID to react to
        reaction: The reaction emoji or type
    """
    body = {"reaction": reaction}
    return await client.request("POST", f"/messages/{message_id}/reactions",
                                json_data=body)


# =============================================================================
# EMAIL FOLDERS (2 tools)
# =============================================================================

@mcp.tool()
async def list_email_folders(account_id: Optional[str] = None) -> dict:
    """List all email folders (inbox, sent, drafts, trash, spam, etc.).

    Args:
        account_id: Email account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)
    """
    acc = account_id or client.email_account_id
    return await client.request("GET", "/folders", account_id=acc)


@mcp.tool()
async def get_email_folder(
    folder_id: str,
    account_id: Optional[str] = None
) -> dict:
    """Get details of a specific email folder.

    Args:
        folder_id: The folder's Unipile ID or provider UID
        account_id: Required when using provider UID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)
    """
    acc = account_id or client.email_account_id
    return await client.request("GET", f"/folders/{folder_id}", account_id=acc)


# =============================================================================
# EMAIL (8 tools — Gmail + Outlook unified, with open/click tracking)
# =============================================================================

@mcp.tool()
async def list_emails(
    account_id: Optional[str] = None,
    limit: int = 100,
    after: Optional[str] = None,
    folder: Optional[str] = None,
    sender: Optional[str] = None,
    recipient: Optional[str] = None
) -> dict:
    """List emails from connected email accounts (Gmail, Outlook, IMAP).

    Args:
        account_id: Email account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)
        limit: Max results (default 100)
        after: Only emails after this ISO8601 datetime (e.g. "2026-02-01T00:00:00Z")
        folder: Filter by folder name (inbox, sent, drafts, etc.)
        sender: Filter by sender email address
        recipient: Filter by recipient email address
    """
    params = {"limit": limit}
    if after:
        params["after"] = after
    if folder:
        params["folder"] = folder
    if sender:
        params["sender"] = sender
    if recipient:
        params["recipient"] = recipient

    acc = account_id or client.email_account_id
    return await client.request("GET", "/emails", params=params, account_id=acc)


@mcp.tool()
async def get_email(email_id: str) -> dict:
    """Get full details of a specific email.

    Args:
        email_id: The email ID

    Returns:
        Email with id, from_attendee, to_attendees, cc_attendees, subject,
        body (HTML), body_plain, attachments, folders, read_date, headers
    """
    return await client.request("GET", f"/emails/{email_id}")


@mcp.tool()
async def send_email(
    to: list[str],
    subject: str,
    body: str,
    account_id: Optional[str] = None,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    reply_to: Optional[str] = None,
    track_opens: bool = False,
    track_links: bool = False,
    tracking_label: Optional[str] = None
) -> dict:
    """Send an email with optional open/click tracking.

    Tracking uses Unipile webhooks — when enabled, you'll receive
    mail_opened events via configured webhooks.

    Args:
        to: List of recipient email addresses
        subject: Email subject line
        body: Email body (HTML supported)
        account_id: Email account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)
        cc: Optional CC recipients
        bcc: Optional BCC recipients
        reply_to: Optional email ID to reply to (for threading)
        track_opens: Enable open tracking via webhooks
        track_links: Enable link click tracking via webhooks
        tracking_label: Custom label for webhook correlation (e.g. "job-app")
    """
    email_data = {
        "to": [{"identifier": addr} for addr in to],
        "subject": subject,
        "body": body
    }

    if cc:
        email_data["cc"] = [{"identifier": addr} for addr in cc]
    if bcc:
        email_data["bcc"] = [{"identifier": addr} for addr in bcc]
    if reply_to:
        email_data["in_reply_to"] = reply_to

    if track_opens or track_links:
        tracking = {}
        if track_opens:
            tracking["opens"] = True
        if track_links:
            tracking["links"] = True
        if tracking_label:
            tracking["label"] = tracking_label
        email_data["tracking_options"] = tracking

    acc = account_id or client.email_account_id
    return await client.request("POST", "/emails", json_data=email_data, account_id=acc)


@mcp.tool()
async def update_email(
    email_id: str,
    read: Optional[bool] = None,
    starred: Optional[bool] = None,
    folder: Optional[str] = None
) -> dict:
    """Update email properties (read status, star, move to folder).

    Args:
        email_id: The email ID
        read: Mark as read (True) or unread (False)
        starred: Star or unstar the email
        folder: Move email to this folder
    """
    body = {}
    if read is not None:
        body["read"] = read
    if starred is not None:
        body["starred"] = starred
    if folder:
        body["folder"] = folder

    return await client.request("PUT", f"/emails/{email_id}", json_data=body)


@mcp.tool()
async def delete_email(email_id: str) -> dict:
    """Delete an email.

    Args:
        email_id: The email ID to delete
    """
    return await client.request("DELETE", f"/emails/{email_id}")


@mcp.tool()
async def get_email_attachment(email_id: str, attachment_id: str) -> dict:
    """Download an email attachment (returns base64-encoded binary).

    Args:
        email_id: The email ID
        attachment_id: The attachment ID

    Returns:
        {content_type, size_bytes, data_base64}
    """
    return await client.request(
        "GET", f"/emails/{email_id}/attachments/{attachment_id}",
        expect_binary=True
    )


@mcp.tool()
async def create_email_draft(
    to: list[str],
    subject: str,
    body: str,
    account_id: Optional[str] = None,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None
) -> dict:
    """Create an email draft (saved but not sent).

    Args:
        to: List of recipient email addresses
        subject: Email subject line
        body: Email body (HTML supported)
        account_id: Email account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)
        cc: Optional CC recipients
        bcc: Optional BCC recipients
    """
    draft_data = {
        "to": [{"identifier": addr} for addr in to],
        "subject": subject,
        "body": body
    }

    if cc:
        draft_data["cc"] = [{"identifier": addr} for addr in cc]
    if bcc:
        draft_data["bcc"] = [{"identifier": addr} for addr in bcc]

    acc = account_id or client.email_account_id
    return await client.request("POST", "/emails/drafts", json_data=draft_data, account_id=acc)


@mcp.tool()
async def list_email_contacts(
    account_id: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List email contacts from connected email accounts.

    Args:
        account_id: Email account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    acc = account_id or client.email_account_id
    return await client.request("GET", "/emails/contacts", params=params, account_id=acc)


# =============================================================================
# CALENDAR (7 tools — Google + Microsoft unified)
# =============================================================================

@mcp.tool()
async def list_calendars(account_id: Optional[str] = None) -> dict:
    """List all calendars from connected accounts (Google Calendar, Outlook).

    Args:
        account_id: Account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID which has calendar access)
    """
    acc = account_id or client.email_account_id
    return await client.request("GET", "/calendars", account_id=acc)


@mcp.tool()
async def get_calendar(
    calendar_id: str,
    account_id: Optional[str] = None
) -> dict:
    """Get details for a specific calendar.

    Args:
        calendar_id: The calendar ID
        account_id: Account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)
    """
    acc = account_id or client.email_account_id
    return await client.request("GET", f"/calendars/{calendar_id}", account_id=acc)


@mcp.tool()
async def list_events(
    calendar_id: str,
    account_id: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List events from a calendar.

    Args:
        calendar_id: The calendar ID
        account_id: Optional account ID
        limit: Max results per page (default 50)
        cursor: Pagination cursor

    Returns:
        Events with id, title, start/end times, attendees, location, etc.
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    acc = account_id or client.email_account_id
    return await client.request("GET", f"/calendars/{calendar_id}/events",
                                params=params, account_id=acc)


@mcp.tool()
async def create_event(
    calendar_id: str,
    title: str,
    start_date_time: str,
    start_time_zone: str,
    end_date_time: str,
    end_time_zone: str,
    account_id: Optional[str] = None,
    body: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[list[dict]] = None,
    recurrence: Optional[list[str]] = None,
    conference: Optional[dict] = None,
    notify: bool = True,
    visibility: Optional[str] = None,
    transparency: Optional[str] = None
) -> dict:
    """Create a calendar event (works with Google Calendar and Outlook).

    Args:
        calendar_id: The calendar ID
        title: Event title
        start_date_time: Start time (ISO8601, e.g. "2026-03-01T10:00:00")
        start_time_zone: Start timezone (e.g. "Asia/Kolkata")
        end_date_time: End time (ISO8601)
        end_time_zone: End timezone
        account_id: Optional account ID
        body: Event description
        location: Event location
        attendees: List of attendee dicts [{email, display_name}]
        recurrence: Recurrence rules (RFC 5545 format)
        conference: Conference details {provider, url}
        notify: Send notifications to attendees (default True)
        visibility: "default", "public", or "private"
        transparency: "opaque" or "transparent"
    """
    event_data = {
        "title": title,
        "start": {"date_time": start_date_time, "time_zone": start_time_zone},
        "end": {"date_time": end_date_time, "time_zone": end_time_zone}
    }

    if body:
        event_data["body"] = body
    if location:
        event_data["location"] = location
    if attendees:
        event_data["attendees"] = attendees
    if recurrence:
        event_data["recurrence"] = recurrence
    if conference:
        event_data["conference"] = conference
    if not notify:
        event_data["notify"] = False
    if visibility:
        event_data["visibility"] = visibility
    if transparency:
        event_data["transparency"] = transparency

    acc = account_id or client.email_account_id
    return await client.request("POST", f"/calendars/{calendar_id}/events",
                                json_data=event_data, account_id=acc)


@mcp.tool()
async def get_event(
    calendar_id: str,
    event_id: str,
    account_id: Optional[str] = None
) -> dict:
    """Get details of a specific calendar event.

    Args:
        calendar_id: The calendar ID
        event_id: The event ID
        account_id: Account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)

    Returns:
        Event with title, body, start/end, attendees, organizer,
        conference, recurrence, visibility, transparency
    """
    acc = account_id or client.email_account_id
    return await client.request("GET", f"/calendars/{calendar_id}/events/{event_id}",
                                account_id=acc)


@mcp.tool()
async def edit_event(
    calendar_id: str,
    event_id: str,
    account_id: Optional[str] = None,
    title: Optional[str] = None,
    start_date_time: Optional[str] = None,
    start_time_zone: Optional[str] = None,
    end_date_time: Optional[str] = None,
    end_time_zone: Optional[str] = None,
    body: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[list[dict]] = None,
    visibility: Optional[str] = None,
    transparency: Optional[str] = None
) -> dict:
    """Edit/update a calendar event (partial update — only send changed fields).

    Args:
        calendar_id: The calendar ID
        event_id: The event ID
        account_id: Optional account ID
        title: Updated title
        start_date_time: Updated start time (ISO8601)
        start_time_zone: Updated start timezone
        end_date_time: Updated end time
        end_time_zone: Updated end timezone
        body: Updated description
        location: Updated location
        attendees: Updated attendees [{email, display_name}]
        visibility: "default", "public", or "private"
        transparency: "opaque" or "transparent"
    """
    event_data = {}

    if title:
        event_data["title"] = title
    if start_date_time or start_time_zone:
        event_data["start"] = {}
        if start_date_time:
            event_data["start"]["date_time"] = start_date_time
        if start_time_zone:
            event_data["start"]["time_zone"] = start_time_zone
    if end_date_time or end_time_zone:
        event_data["end"] = {}
        if end_date_time:
            event_data["end"]["date_time"] = end_date_time
        if end_time_zone:
            event_data["end"]["time_zone"] = end_time_zone
    if body:
        event_data["body"] = body
    if location:
        event_data["location"] = location
    if attendees is not None:
        event_data["attendees"] = attendees
    if visibility:
        event_data["visibility"] = visibility
    if transparency:
        event_data["transparency"] = transparency

    acc = account_id or client.email_account_id
    return await client.request("PATCH", f"/calendars/{calendar_id}/events/{event_id}",
                                json_data=event_data, account_id=acc)


@mcp.tool()
async def delete_event(
    calendar_id: str,
    event_id: str,
    account_id: Optional[str] = None
) -> dict:
    """Delete a calendar event.

    Args:
        calendar_id: The calendar ID
        event_id: The event ID to delete
        account_id: Account ID (defaults to UNIPILE_EMAIL_ACCOUNT_ID)
    """
    acc = account_id or client.email_account_id
    return await client.request("DELETE", f"/calendars/{calendar_id}/events/{event_id}",
                                account_id=acc)


# =============================================================================
# LINKEDIN SEARCH (5 tools)
# =============================================================================

@mcp.tool()
async def search_people(
    keywords: Optional[str] = None,
    location: Optional[list[str]] = None,
    industry: Optional[list[str]] = None,
    company: Optional[list[str]] = None,
    past_company: Optional[list[str]] = None,
    network_distance: Optional[list[int]] = None,
    profile_language: Optional[list[str]] = None,
    limit: int = 25,
    cursor: Optional[str] = None
) -> dict:
    """Search for people on LinkedIn using Classic LinkedIn filters.

    Use get_search_params() to find valid IDs for location, industry, and company.

    Args:
        keywords: Free text search (name, title, company, etc.)
        location: List of location IDs
        industry: List of industry IDs
        company: List of current company IDs
        past_company: List of past company IDs
        network_distance: Connection degree [1, 2, 3]
        profile_language: ISO language codes (e.g., ["en"])
        limit: Max results (1-50, default 25)
        cursor: Pagination cursor
    """
    body = {
        "api": "classic",
        "category": "people",
        "limit": min(limit, 50)
    }

    if keywords:
        body["keywords"] = keywords
    if location:
        body["location"] = location
    if industry:
        body["industry"] = industry
    if company:
        body["company"] = company
    if past_company:
        body["past_company"] = past_company
    if network_distance:
        body["network_distance"] = network_distance
    if profile_language:
        body["profile_language"] = profile_language
    if cursor:
        body["cursor"] = cursor

    return await client.request("POST", "/linkedin/search", json_data=body,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def search_people_sales_nav(
    keywords: Optional[str] = None,
    location: Optional[list[str]] = None,
    industry: Optional[list[str]] = None,
    company: Optional[list[str]] = None,
    past_company: Optional[list[str]] = None,
    network_distance: Optional[list[int]] = None,
    profile_language: Optional[list[str]] = None,
    tenure: Optional[dict] = None,
    seniority_level: Optional[list[str]] = None,
    function: Optional[list[str]] = None,
    company_headcount: Optional[list[dict]] = None,
    changed_jobs: Optional[bool] = None,
    posted_on_linkedin: Optional[bool] = None,
    limit: int = 25,
    cursor: Optional[str] = None
) -> dict:
    """Search for people using LinkedIn Sales Navigator (requires Sales Nav subscription).

    Args:
        keywords: Free text search
        location: List of location IDs
        industry: List of industry IDs
        company: List of current company IDs
        past_company: List of past company IDs
        network_distance: Connection degree [1, 2, 3]
        profile_language: ISO language codes
        tenure: Years at current company, e.g., {"min": 1, "max": 5}
        seniority_level: Job levels (e.g., ["Director", "VP", "CXO"])
        function: Job functions (e.g., ["Engineering", "Sales"])
        company_headcount: Company size ranges
        changed_jobs: True to find people who recently changed jobs
        posted_on_linkedin: True to find active posters
        limit: Max results (1-100, default 25)
        cursor: Pagination cursor
    """
    body = {
        "api": "sales_navigator",
        "category": "people",
        "limit": min(limit, 100)
    }

    if keywords:
        body["keywords"] = keywords
    if location:
        body["location"] = location
    if industry:
        body["industry"] = industry
    if company:
        body["company"] = company
    if past_company:
        body["past_company"] = past_company
    if network_distance:
        body["network_distance"] = network_distance
    if profile_language:
        body["profile_language"] = profile_language
    if tenure:
        body["tenure"] = tenure
    if seniority_level:
        body["seniority_level"] = seniority_level
    if function:
        body["function"] = function
    if company_headcount:
        body["company_headcount"] = company_headcount
    if changed_jobs is not None:
        body["changed_jobs"] = changed_jobs
    if posted_on_linkedin is not None:
        body["posted_on_linkedin"] = posted_on_linkedin
    if cursor:
        body["cursor"] = cursor

    return await client.request("POST", "/linkedin/search", json_data=body,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def search_companies(
    keywords: Optional[str] = None,
    industry: Optional[list[str]] = None,
    location: Optional[list[str]] = None,
    headcount_min: Optional[int] = None,
    headcount_max: Optional[int] = None,
    has_job_offers: Optional[bool] = None,
    limit: int = 25,
    cursor: Optional[str] = None
) -> dict:
    """Search for companies on LinkedIn.

    Args:
        keywords: Company name or description keywords
        industry: List of industry IDs
        location: List of location IDs (headquarters)
        headcount_min: Minimum employee count
        headcount_max: Maximum employee count
        has_job_offers: True to find companies currently hiring
        limit: Max results (1-50, default 25)
        cursor: Pagination cursor
    """
    body = {
        "api": "classic",
        "category": "companies",
        "limit": min(limit, 50)
    }

    if keywords:
        body["keywords"] = keywords
    if industry:
        body["industry"] = industry
    if location:
        body["location"] = location
    if headcount_min is not None or headcount_max is not None:
        body["headcount"] = {}
        if headcount_min is not None:
            body["headcount"]["min"] = headcount_min
        if headcount_max is not None:
            body["headcount"]["max"] = headcount_max
    if has_job_offers is not None:
        body["has_job_offers"] = has_job_offers
    if cursor:
        body["cursor"] = cursor

    return await client.request("POST", "/linkedin/search", json_data=body,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def search_posts(
    keywords: str,
    sort_by: Optional[str] = None,
    date_posted: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 25,
    cursor: Optional[str] = None
) -> dict:
    """Search for LinkedIn posts/content.

    Args:
        keywords: Content keywords to search for (required)
        sort_by: "relevance" or "date"
        date_posted: "past_day", "past_week", or "past_month"
        content_type: "videos", "images", or "documents"
        limit: Max results (1-50, default 25)
        cursor: Pagination cursor
    """
    body = {
        "api": "classic",
        "category": "posts",
        "keywords": keywords,
        "limit": min(limit, 50)
    }

    if sort_by:
        body["sort_by"] = sort_by
    if date_posted:
        body["date_posted"] = date_posted
    if content_type:
        body["content_type"] = content_type
    if cursor:
        body["cursor"] = cursor

    return await client.request("POST", "/linkedin/search", json_data=body,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def get_search_params(
    param_type: str,
    query: Optional[str] = None
) -> dict:
    """Get valid parameter IDs for LinkedIn search filters.

    Args:
        param_type: Parameter type - LOCATION, INDUSTRY, COMPANY, SCHOOL,
                    PEOPLE, JOB_FUNCTION, JOB_TITLE, SKILL, REGION, etc.
        query: Optional search string to filter results
    """
    params = {"type": param_type.upper()}
    if query:
        params["q"] = query

    return await client.request("GET", "/linkedin/search/parameters", params=params,
                                account_id=client.linkedin_account_id)


# =============================================================================
# LINKEDIN PROFILES & USERS (7 tools)
# =============================================================================

@mcp.tool()
async def get_profile(
    provider_id: str,
    sections: Optional[list[str]] = None
) -> dict:
    """Get a LinkedIn user's full profile.

    Args:
        provider_id: The LinkedIn provider ID
        sections: Optional sections: about, experience, education, skills,
                  certifications, languages, projects, recommendations_received
    """
    params = {}
    if sections:
        params["sections"] = ",".join(sections)

    return await client.request("GET", f"/users/{provider_id}", params=params,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def get_company_profile(company_id: str) -> dict:
    """Get a company's LinkedIn profile/page details.

    Args:
        company_id: The LinkedIn company ID or vanity URL name
    """
    return await client.request("GET", f"/linkedin/company/{company_id}",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def edit_own_profile(
    headline: Optional[str] = None,
    summary: Optional[str] = None,
    location: Optional[str] = None,
    account_id: Optional[str] = None
) -> dict:
    """Edit your own LinkedIn profile fields.

    Args:
        headline: New profile headline
        summary: New profile summary/about section
        location: New location string
        account_id: Optional account ID (defaults to LinkedIn account)
    """
    acc = account_id or client.linkedin_account_id
    body = {"type": "LINKEDIN"}
    if headline:
        body["headline"] = headline
    if summary:
        body["summary"] = summary
    if location:
        body["location"] = location
    return await client.request("PATCH", "/users/me/edit", json_data=body,
                                account_id=acc)


@mcp.tool()
async def list_followers(
    limit: int = 50,
    cursor: Optional[str] = None,
    account_id: Optional[str] = None
) -> dict:
    """List your LinkedIn followers.

    Args:
        limit: Max results (default 50)
        cursor: Pagination cursor
        account_id: Optional account ID (defaults to LinkedIn account)
    """
    acc = account_id or client.linkedin_account_id
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await client.request("GET", "/users/followers", params=params,
                                account_id=acc)


@mcp.tool()
async def list_following(
    limit: int = 50,
    cursor: Optional[str] = None,
    account_id: Optional[str] = None
) -> dict:
    """List LinkedIn users/companies you are following.

    Args:
        limit: Max results (default 50)
        cursor: Pagination cursor
        account_id: Optional account ID (defaults to LinkedIn account)
    """
    acc = account_id or client.linkedin_account_id
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await client.request("GET", "/users/following", params=params,
                                account_id=acc)


@mcp.tool()
async def list_user_comments(
    identifier: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    account_id: Optional[str] = None
) -> dict:
    """List comments made by a LinkedIn user.

    Args:
        identifier: The user's LinkedIn provider ID or public identifier
        limit: Max results (default 50)
        cursor: Pagination cursor
        account_id: Optional account ID (defaults to LinkedIn account)
    """
    acc = account_id or client.linkedin_account_id
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await client.request("GET", f"/users/{identifier}/comments",
                                params=params, account_id=acc)


@mcp.tool()
async def list_user_reactions(
    identifier: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    account_id: Optional[str] = None
) -> dict:
    """List reactions made by a LinkedIn user.

    Args:
        identifier: The user's LinkedIn provider ID or public identifier
        limit: Max results (default 50)
        cursor: Pagination cursor
        account_id: Optional account ID (defaults to LinkedIn account)
    """
    acc = account_id or client.linkedin_account_id
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await client.request("GET", f"/users/{identifier}/reactions",
                                params=params, account_id=acc)


# =============================================================================
# LINKEDIN CONNECTIONS & INVITATIONS (7 tools)
# =============================================================================

@mcp.tool()
async def send_invitation(
    provider_id: str,
    message: Optional[str] = None
) -> dict:
    """Send a LinkedIn connection request.

    Args:
        provider_id: LinkedIn provider ID of the person to connect with
        message: Optional personalized message (max 300 characters)
    """
    body = {"provider_id": provider_id}

    if message:
        if len(message) > 300:
            return {"error": "Invitation message must be 300 characters or less"}
        body["message"] = message

    return await client.request("POST", "/users/invite", json_data=body,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def list_invitations_sent(
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List pending outbound LinkedIn connection requests.

    Args:
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", "/users/invite/sent", params=params,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def list_invitations_received(
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List inbound LinkedIn connection requests.

    Args:
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", "/users/invite/received", params=params,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def accept_invitation(invitation_id: str) -> dict:
    """Accept a received LinkedIn connection request.

    Args:
        invitation_id: The invitation ID (from list_invitations_received)
    """
    return await client.request("POST", f"/users/invite/received/{invitation_id}",
                                json_data={"action": "accept"},
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def decline_invitation(invitation_id: str) -> dict:
    """Decline a received LinkedIn connection request.

    Args:
        invitation_id: The invitation ID (from list_invitations_received)
    """
    return await client.request("POST", f"/users/invite/received/{invitation_id}",
                                json_data={"action": "decline"},
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def cancel_invitation(invitation_id: str) -> dict:
    """Withdraw a sent LinkedIn connection request.

    Args:
        invitation_id: The invitation ID (from list_invitations_sent)
    """
    return await client.request("DELETE", f"/users/invite/{invitation_id}",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def list_relations(
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List your 1st degree LinkedIn connections.

    Args:
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", "/users/relations", params=params,
                                account_id=client.linkedin_account_id)


# =============================================================================
# LINKEDIN INMAIL (2 tools — requires Premium)
# =============================================================================

@mcp.tool()
async def send_inmail(
    attendees_ids: list[str],
    subject: str,
    text: str
) -> dict:
    """Send InMail to non-connections (requires LinkedIn Premium/Sales Nav).

    Args:
        attendees_ids: List of LinkedIn provider IDs
        subject: InMail subject line
        text: Message body
    """
    body = {
        "attendees_ids": attendees_ids,
        "subject": subject,
        "text": text,
        "linkedin": {"inmail": True}
    }

    return await client.request("POST", "/chats", json_data=body,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def get_inmail_credits() -> dict:
    """Check remaining LinkedIn InMail credits."""
    return await client.request("GET", "/linkedin/inmail_balance",
                                account_id=client.linkedin_account_id)


# =============================================================================
# LINKEDIN POSTS & CONTENT (6 tools)
# =============================================================================

@mcp.tool()
async def get_post(post_id: str) -> dict:
    """Get a specific LinkedIn post by ID.

    Args:
        post_id: The post ID
    """
    return await client.request("GET", f"/posts/{post_id}",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def create_post(text: str) -> dict:
    """Create a new LinkedIn post.

    Args:
        text: The post content text
    """
    body = {"text": text}
    return await client.request("POST", "/posts", json_data=body,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def list_post_comments(
    post_id: str,
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List comments on a LinkedIn post.

    Args:
        post_id: The post ID
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", f"/posts/{post_id}/comments",
                                params=params, account_id=client.linkedin_account_id)


@mcp.tool()
async def comment_on_post(post_id: str, text: str) -> dict:
    """Comment on a LinkedIn post.

    Args:
        post_id: The post ID to comment on
        text: The comment text
    """
    body = {"text": text}
    return await client.request("POST", f"/posts/{post_id}/comments",
                                json_data=body, account_id=client.linkedin_account_id)


@mcp.tool()
async def react_to_post(
    post_id: str,
    reaction_type: str = "LIKE"
) -> dict:
    """React to a LinkedIn post.

    Args:
        post_id: The post ID to react to
        reaction_type: Reaction type - LIKE, CELEBRATE, SUPPORT, FUNNY,
                       LOVE, INSIGHTFUL, CURIOUS
    """
    body = {"reaction_type": reaction_type}
    return await client.request("POST", f"/posts/{post_id}/reactions",
                                json_data=body, account_id=client.linkedin_account_id)


@mcp.tool()
async def list_post_reactions(
    post_id: str,
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List reactions on a LinkedIn post.

    Args:
        post_id: The post ID
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", f"/posts/{post_id}/reactions",
                                params=params, account_id=client.linkedin_account_id)


# =============================================================================
# LINKEDIN JOBS & RECRUITER (13 tools)
# =============================================================================

@mcp.tool()
async def list_jobs() -> dict:
    """List LinkedIn job postings managed by your account."""
    return await client.request("GET", "/linkedin/jobs",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def get_job(job_id: str) -> dict:
    """Get details of a specific LinkedIn job posting.

    Args:
        job_id: The job ID
    """
    return await client.request("GET", f"/linkedin/jobs/{job_id}",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def create_job(
    title: str,
    description: str,
    location: str,
    company_id: str
) -> dict:
    """Create a new LinkedIn job posting.

    Args:
        title: Job title
        description: Job description (HTML supported)
        location: Job location
        company_id: LinkedIn company ID to post under
    """
    body = {
        "title": title,
        "description": description,
        "location": location,
        "company_id": company_id
    }
    return await client.request("POST", "/linkedin/jobs", json_data=body,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def edit_job(
    job_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None
) -> dict:
    """Edit a LinkedIn job posting (partial update).

    Args:
        job_id: The job ID
        title: Updated job title
        description: Updated description
        location: Updated location
    """
    body = {}
    if title:
        body["title"] = title
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    return await client.request("PATCH", f"/linkedin/jobs/{job_id}",
                                json_data=body, account_id=client.linkedin_account_id)


@mcp.tool()
async def publish_job(job_id: str) -> dict:
    """Publish a draft LinkedIn job posting.

    Args:
        job_id: The job ID to publish
    """
    return await client.request("POST", f"/linkedin/jobs/{job_id}/publish",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def close_job(job_id: str) -> dict:
    """Close an active LinkedIn job posting.

    Args:
        job_id: The job ID to close
    """
    return await client.request("POST", f"/linkedin/jobs/{job_id}/close",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def get_job_applicants(
    job_id: str,
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List applicants for a LinkedIn job posting.

    Args:
        job_id: The job ID
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", f"/linkedin/jobs/{job_id}/applicants",
                                params=params, account_id=client.linkedin_account_id)


@mcp.tool()
async def get_applicant_resume(job_id: str, applicant_id: str) -> dict:
    """Download an applicant's resume (returns base64-encoded binary).

    Args:
        job_id: The job ID
        applicant_id: The applicant ID

    Returns:
        {content_type, size_bytes, data_base64}
    """
    return await client.request(
        "GET", f"/linkedin/jobs/{job_id}/applicants/{applicant_id}/resume",
        account_id=client.linkedin_account_id, expect_binary=True
    )


@mcp.tool()
async def get_job_applicant(
    applicant_id: str,
    service: Optional[str] = None
) -> dict:
    """Get details of a single job applicant.

    Args:
        applicant_id: The applicant ID
        service: Optional service parameter (e.g. 'LINKEDIN', 'LINKEDIN_RECRUITER')
    """
    params = {}
    if service:
        params["service"] = service
    return await client.request("GET", f"/linkedin/jobs/applicants/{applicant_id}",
                                params=params if params else None,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def get_hiring_projects(
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List LinkedIn Recruiter hiring projects.

    Args:
        limit: Max results (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await client.request("GET", "/linkedin/projects", params=params,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def get_hiring_project(project_id: str) -> dict:
    """Get details of a single LinkedIn Recruiter hiring project.

    Args:
        project_id: The hiring project ID
    """
    return await client.request("GET", f"/linkedin/projects/{project_id}",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def perform_linkedin_action(
    user_id: str,
    action: str,
    api: str = "LINKEDIN",
    account_id: Optional[str] = None
) -> dict:
    """Perform an action on a LinkedIn user (follow, unfollow, block, save lead, etc.).

    Args:
        user_id: The LinkedIn user/provider ID
        action: Action to perform: 'follow', 'unfollow', 'block', 'unblock', 'saveLead', 'removeLead'
        api: API type (default 'LINKEDIN', can be 'LINKEDIN_RECRUITER')
        account_id: Optional account ID (defaults to LinkedIn account)
    """
    acc = account_id or client.linkedin_account_id
    body = {"api": api, "action": action}
    return await client.request("POST", f"/linkedin/user/{user_id}",
                                json_data=body, account_id=acc)


@mcp.tool()
async def solve_job_checkpoint(
    draft_id: str,
    input_value: str
) -> dict:
    """Solve a checkpoint/verification during LinkedIn job publishing.

    Args:
        draft_id: The draft job ID that requires verification
        input_value: The verification input (e.g. confirmation code)
    """
    body = {"input": input_value}
    return await client.request("POST", f"/linkedin/jobs/{draft_id}/checkpoint",
                                json_data=body, account_id=client.linkedin_account_id)


# =============================================================================
# WEBHOOKS (3 tools)
# =============================================================================

@mcp.tool()
async def list_webhooks(
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List all configured webhooks.

    Args:
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", "/webhooks", params=params)


@mcp.tool()
async def create_webhook(
    name: str,
    request_url: str,
    account_ids: list[str],
    events: list[str],
    format: str = "json",
    headers: Optional[list[dict]] = None
) -> dict:
    """Create a webhook to receive real-time events.

    Available events:
    - Messaging: message_received, message_sent, message_read, message_deleted
    - Email: mail_received, mail_sent, mail_opened (tracking)
    - Calendar: calendar_event_created, calendar_event_updated, calendar_event_deleted
    - Posts: post_created, post_reaction, post_comment
    - Relations: new_relation, relation_removed
    - Account: creation_success, creation_failure, account_disconnected

    Args:
        name: Webhook name
        request_url: URL to receive webhook POST requests
        account_ids: List of account IDs to monitor
        events: List of event types to subscribe to
        format: Response format - "json" or "xml" (default "json")
        headers: Optional custom headers [{key, value}] to include in webhook requests
    """
    body = {
        "name": name,
        "request_url": request_url,
        "account_ids": account_ids,
        "events": events,
        "format": format
    }

    if headers:
        body["headers"] = headers

    return await client.request("POST", "/webhooks", json_data=body)


@mcp.tool()
async def delete_webhook(webhook_id: str) -> dict:
    """Delete a webhook.

    Args:
        webhook_id: The webhook ID to delete
    """
    return await client.request("DELETE", f"/webhooks/{webhook_id}")


# =============================================================================
# ADVANCED (4 tools)
# =============================================================================

@mcp.tool()
async def endorse_skill(
    provider_id: str,
    skill_name: str
) -> dict:
    """Endorse a skill on someone's LinkedIn profile.

    Args:
        provider_id: The LinkedIn provider ID of the person
        skill_name: The skill name to endorse
    """
    return await client.request("POST", f"/users/{provider_id}/skill/{skill_name}",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def raw_linkedin_request(
    method: str,
    request_url: str,
    body: Optional[dict] = None
) -> dict:
    """Make a raw LinkedIn API request through Unipile (escape hatch).

    Use this for LinkedIn API endpoints not covered by other tools.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        request_url: The LinkedIn API URL path
        body: Optional request body
    """
    json_data = {
        "method": method,
        "request_url": request_url
    }
    if body:
        json_data["body"] = body

    return await client.request("POST", "/linkedin", json_data=json_data,
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def get_profile_visitors() -> dict:
    """Get a list of people who recently viewed your LinkedIn profile."""
    return await client.request("GET", "/users/me/profile_visitors",
                                account_id=client.linkedin_account_id)


@mcp.tool()
async def list_user_posts(
    provider_id: str,
    limit: int = 50,
    cursor: Optional[str] = None
) -> dict:
    """List posts by a specific LinkedIn user.

    Args:
        provider_id: The LinkedIn provider ID of the user
        limit: Max results per page (default 50)
        cursor: Pagination cursor
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    return await client.request("GET", f"/users/{provider_id}/posts",
                                params=params, account_id=client.linkedin_account_id)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
