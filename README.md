# mcp-server-unipile

A comprehensive [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for the [Unipile API](https://developer.unipile.com) — **95 tools** covering the full API surface.

Connect your AI assistant to LinkedIn, Email, Calendar, WhatsApp, Instagram, and Telegram through a single unified interface.

## Features

| Category | Tools | Capabilities |
|----------|-------|-------------|
| **Account Management** | 10 | List, get, connect, delete, reconnect, resync, restart accounts + 2FA checkpoints |
| **Messaging** | 14 | Cross-platform chat (LinkedIn, WhatsApp, Instagram, Telegram) with search, reactions, forwarding |
| **Attendees** | 6 | Contact management, profile pictures, chat history by person |
| **Email** | 11 | Send, read, search, draft, track opens/clicks (Gmail + Outlook unified) |
| **Calendar** | 7 | Events, scheduling, free/busy queries (Google + Microsoft unified) |
| **LinkedIn Search** | 6 | People, companies, posts, **jobs** (candidate-side), Sales Navigator |
| **LinkedIn Profiles** | 7 | View/edit profiles, followers, following, user activity |
| **LinkedIn Connections** | 7 | Invitations, relations, connection management |
| **LinkedIn InMail** | 2 | Send InMail, check credits |
| **LinkedIn Posts** | 6 | Create, comment, react, view engagement |
| **LinkedIn Jobs** | 13 | Job search, posting, applicant management, recruiter features |
| **Webhooks** | 3 | Real-time event notifications |
| **Advanced** | 3 | Profile visitors, raw API access, skill endorsements |

## Installation

### Using uvx (recommended)

```bash
uvx mcp-server-unipile
```

### Using pip

```bash
pip install mcp-server-unipile
```

### From source

```bash
git clone https://github.com/Sundeepg98/mcp-server-unipile.git
cd mcp-server-unipile
pip install -e .
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `UNIPILE_BASE_URL` | Yes | Your Unipile API base URL (e.g., `https://apiX.unipile.com:XXXXX/api/v1`) |
| `UNIPILE_API_KEY` | Yes | Your Unipile API key |
| `UNIPILE_LINKEDIN_ACCOUNT_ID` | No | Default LinkedIn account ID (avoids passing it to every LinkedIn tool) |
| `UNIPILE_EMAIL_ACCOUNT_ID` | No | Default email account ID (avoids passing it to every email/calendar tool) |

Get your API credentials from the [Unipile Dashboard](https://app.unipile.com).

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "unipile": {
      "command": "uvx",
      "args": ["mcp-server-unipile"],
      "env": {
        "UNIPILE_BASE_URL": "https://apiX.unipile.com:XXXXX/api/v1",
        "UNIPILE_API_KEY": "your_api_key",
        "UNIPILE_LINKEDIN_ACCOUNT_ID": "your_linkedin_id",
        "UNIPILE_EMAIL_ACCOUNT_ID": "your_email_id"
      }
    }
  }
}
```

### Claude Code

Add to your `.claude.json` (user or project scope):

```json
{
  "mcpServers": {
    "unipile": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-unipile"],
      "env": {
        "UNIPILE_BASE_URL": "https://apiX.unipile.com:XXXXX/api/v1",
        "UNIPILE_API_KEY": "your_api_key",
        "UNIPILE_LINKEDIN_ACCOUNT_ID": "your_linkedin_id",
        "UNIPILE_EMAIL_ACCOUNT_ID": "your_email_id"
      }
    }
  }
}
```

### VS Code / Cursor

Add to your `.vscode/mcp.json`:

```json
{
  "servers": {
    "unipile": {
      "command": "uvx",
      "args": ["mcp-server-unipile"],
      "env": {
        "UNIPILE_BASE_URL": "https://apiX.unipile.com:XXXXX/api/v1",
        "UNIPILE_API_KEY": "your_api_key"
      }
    }
  }
}
```

## Prerequisites

1. A [Unipile](https://unipile.com) account with API access
2. At least one connected account (LinkedIn, Gmail, WhatsApp, etc.) in your Unipile dashboard
3. Python 3.10+

## Usage Examples

### Search for jobs

```
Search for remote Python developer jobs posted this week
```
Your AI assistant will call `search_jobs` with keywords, remote_policy, and posted_at filters.

### Send a LinkedIn message

```
Message John Smith on LinkedIn asking about the engineering role at his company
```
Uses `search_people` to find John, then `send_message` to reach out.

### Manage email

```
Show me unread emails from today and draft a reply to the one from HR
```
Uses `list_emails` with filters, then `draft_email` for the response.

### Track engagement

```
Who viewed my LinkedIn profile this week? Also show my latest followers.
```
Uses `get_profile_visitors` and `list_followers`.

## All 95 Tools

<details>
<summary>Account Management (10)</summary>

- `list_accounts` - List all connected accounts
- `get_account` - Get single account details
- `connect_account` - Connect via native auth (username/password)
- `reconnect_account` - Reconnect via hosted auth (returns browser URL)
- `delete_account` - Remove an account
- `resync_account` - Force full data resync
- `restart_account` - Restart sync processes
- `solve_checkpoint` - Solve 2FA/checkpoint challenge
- `resend_checkpoint` - Resend verification code
- `get_my_profile` - Get your own profile

</details>

<details>
<summary>Messaging (14)</summary>

- `list_chats` - List conversations (filterable by account/platform)
- `get_chat` - Get conversation details
- `get_chat_messages` - List messages in a chat
- `get_message` - Get single message details
- `send_message` - Send a message in a chat
- `forward_message` - Forward a message
- `get_message_attachment` - Download attachment
- `start_chat` - Start new conversation
- `update_chat` - Mark read/unread, archive
- `sync_chat` - Sync conversation history
- `list_all_messages` - Cross-chat message search
- `delete_chat` - Delete a conversation
- `delete_message` - Delete a message
- `list_chat_attendees` - List participants in a chat

</details>

<details>
<summary>Attendees (6)</summary>

- `list_attendees` - List all contacts/attendees
- `get_attendee` - Get attendee details
- `get_attendee_picture` - Download profile picture (base64)
- `list_chats_by_attendee` - Find chats with specific person
- `list_messages_by_attendee` - Messages from specific person
- `add_message_reaction` - React to a message

</details>

<details>
<summary>Email (11)</summary>

- `list_emails` - List emails with filters
- `get_email` - Read a specific email
- `send_email` - Send email with optional open/click tracking
- `draft_email` - Create email draft
- `delete_email` - Delete email
- `get_email_attachment` - Download email attachment
- `list_email_contacts` - List email contacts
- `update_email` - Modify email (read/star/move)
- `list_email_folders` - List folders (inbox, sent, drafts, etc.)
- `get_email_folder` - Get folder details
- `list_email_labels` - List Gmail labels

</details>

<details>
<summary>Calendar (7)</summary>

- `list_calendars` - List all calendars
- `get_calendar` - Get calendar details
- `list_events` - List calendar events
- `get_event` - Get event details
- `create_event` - Create calendar event
- `edit_event` - Modify event
- `delete_event` - Delete event

</details>

<details>
<summary>LinkedIn Search (6)</summary>

- `search_people` - Search LinkedIn members
- `search_people_sales_nav` - Sales Navigator advanced search
- `search_companies` - Search companies
- `search_posts` - Search LinkedIn content
- `search_jobs` - Search job postings (candidate-side, with Easy Apply flag)
- `get_search_params` - Get valid filter IDs (locations, industries, etc.)

</details>

<details>
<summary>LinkedIn Profiles & Users (7)</summary>

- `get_profile` - Get a user's LinkedIn profile
- `get_company_profile` - Get company page details
- `edit_own_profile` - Edit your headline/summary/location
- `list_followers` - List your followers
- `list_following` - List who you follow
- `list_user_comments` - User's comment history
- `list_user_reactions` - User's reaction history

</details>

<details>
<summary>LinkedIn Connections (7)</summary>

- `send_invitation` - Send connection request
- `accept_invitation` - Accept connection request
- `decline_invitation` - Decline request
- `cancel_invitation` - Cancel sent request
- `list_invitations_sent` - View sent invitations
- `list_invitations_received` - View received invitations
- `list_relations` - List all connections

</details>

<details>
<summary>LinkedIn InMail (2)</summary>

- `send_inmail` - Send InMail message
- `get_inmail_credits` - Check remaining credits

</details>

<details>
<summary>LinkedIn Posts (6)</summary>

- `create_post` - Create LinkedIn post
- `get_post` - Get post details
- `comment_on_post` - Comment on a post
- `react_to_post` - React to a post
- `list_post_comments` - List post comments
- `list_post_reactions` - List post reactions

</details>

<details>
<summary>LinkedIn Jobs & Recruiter (13)</summary>

- `search_jobs` - Search job postings as candidate
- `list_jobs` - List your job postings
- `get_job` - Get job posting details
- `create_job` - Create job posting
- `edit_job` - Edit job posting
- `publish_job` - Publish draft job
- `close_job` - Close job posting
- `get_job_applicants` - List applicants
- `get_job_applicant` - Get applicant details
- `get_applicant_resume` - Download applicant resume
- `get_hiring_projects` - List Recruiter hiring projects
- `get_hiring_project` - Get project details
- `perform_linkedin_action` - Follow/unfollow/block users
- `solve_job_checkpoint` - Solve job publishing checkpoint

</details>

<details>
<summary>Webhooks (3)</summary>

- `list_webhooks` - List configured webhooks
- `create_webhook` - Create webhook
- `delete_webhook` - Delete webhook

</details>

<details>
<summary>Advanced (3)</summary>

- `get_profile_visitors` - Who viewed your profile
- `endorse_skill` - Endorse a connection's skill
- `raw_linkedin_request` - Raw LinkedIn API request
- `list_user_posts` - List a user's posts

</details>

## How It Works

This server wraps the [Unipile REST API](https://developer.unipile.com) into MCP tools. Unipile acts as a unified layer over multiple platforms:

```
Your AI Assistant
      |
      v
  MCP Server (this package)
      |
      v
  Unipile API
      |
      v
  LinkedIn | Gmail | WhatsApp | Instagram | Telegram | Outlook
```

Each tool maps to one Unipile API endpoint. Authentication is handled via API key. Account-specific operations use either the default account IDs from environment variables or accept explicit `account_id` parameters.

## License

MIT
