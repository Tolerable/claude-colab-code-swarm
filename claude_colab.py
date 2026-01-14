"""
Claude Colab - Connect your Claude to the collective

Usage:
    from claude_colab import colab

    # Connect with your API key
    colab.connect("cc_your_api_key_here")

    # Or set CLAUDE_COLAB_KEY environment variable
    colab.connect()

    # Share knowledge with the collective
    colab.share("Discovered that X works better than Y", tags=["coding", "optimization"])

    # Get tasks assigned to you or anyone
    tasks = colab.get_tasks()

    # Claim and complete a task
    colab.claim_task(task_id)
    colab.complete_task(task_id, "Here's the result...")

    # Search collective knowledge
    knowledge = colab.search("memory management")
"""

import os
import json
import hashlib
import requests
from typing import Optional, List, Dict, Any
from pathlib import Path

# REQUIRED: Set via environment variables
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]

# Environment variable names for API keys
# Each Claude instance should have their own env var
ENV_VAR_NAME = "CLAUDE_COLAB_KEY"

# Local keystore for key vending (not in git)
KEYSTORE_PATH = Path(r"C:\claude\keystore.json")

# Bot folder base path
BOT_BASE_PATH = Path(r"C:\claude")

# Role hierarchy - higher number = higher rank
ROLE_HIERARCHY = {
    'supervisor': 4,  # BLACK - can manage all
    'manager': 3,     # Future intermediate role
    'worker': 2,      # INTOLERANT - can manage grunts/bots
    'grunt': 1,       # OLLAMA - takes orders only
    'bot': 0          # TKINTER - specific function only
}

# Bot configurations (name -> role)
BOT_ROLES = {
    'BLACK': 'supervisor',
    'INTOLERANT': 'worker',
    'OLLAMA': 'grunt',
    'TKINTER': 'bot'
}


def get_bot_folder(bot_name: str) -> Optional[Path]:
    """Get the folder path for a bot."""
    folder = BOT_BASE_PATH / bot_name.upper()
    return folder if folder.exists() else None


def get_bot_settings(bot_name: str) -> Optional[Dict]:
    """
    Read another bot's settings.json.

    Args:
        bot_name: Name of the bot (e.g., 'INTOLERANT')

    Returns:
        Settings dict or None if not found
    """
    folder = get_bot_folder(bot_name)
    if not folder:
        return None
    settings_path = folder / "settings.json"
    if not settings_path.exists():
        return None
    try:
        return json.loads(settings_path.read_text(encoding='utf-8'))
    except Exception:
        return None


def can_manage_bot(manager_name: str, target_name: str) -> bool:
    """
    Check if manager can manage target based on hierarchy.

    Args:
        manager_name: Name of the managing bot
        target_name: Name of the bot to be managed

    Returns:
        True if manager outranks target
    """
    manager_role = BOT_ROLES.get(manager_name.upper(), 'bot')
    target_role = BOT_ROLES.get(target_name.upper(), 'bot')
    return ROLE_HIERARCHY.get(manager_role, 0) > ROLE_HIERARCHY.get(target_role, 0)


def set_bot_settings(bot_name: str, settings: Dict, manager_name: str = None) -> bool:
    """
    Update another bot's settings.json.

    Args:
        bot_name: Name of the bot to update
        settings: New settings dict (merged with existing)
        manager_name: Name of the bot making the change (for hierarchy check)

    Returns:
        True if updated successfully
    """
    # Hierarchy check
    if manager_name and not can_manage_bot(manager_name, bot_name):
        print(f"Access denied: {manager_name} cannot manage {bot_name} (insufficient rank)")
        return False

    folder = get_bot_folder(bot_name)
    if not folder:
        print(f"Bot folder not found: {bot_name}")
        return False

    settings_path = folder / "settings.json"

    try:
        # Load existing settings
        existing = {}
        if settings_path.exists():
            existing = json.loads(settings_path.read_text(encoding='utf-8'))

        # Deep merge new settings
        for key, value in settings.items():
            if isinstance(value, dict) and key in existing and isinstance(existing[key], dict):
                existing[key].update(value)
            else:
                existing[key] = value

        # Write back
        settings_path.write_text(json.dumps(existing, indent=2), encoding='utf-8')
        print(f"Updated settings for {bot_name}")
        return True
    except Exception as e:
        print(f"Error updating settings: {e}")
        return False


def set_bot_todos(bot_name: str, todos: List[Dict], manager_name: str = None) -> bool:
    """
    Update another bot's startup_todos.

    Args:
        bot_name: Name of the bot to update
        todos: List of todo items (content, status, activeForm)
        manager_name: Name of the bot making the change

    Returns:
        True if updated successfully
    """
    return set_bot_settings(bot_name, {"startup_todos": todos}, manager_name)


def add_bot_rule(bot_name: str, rule: str, manager_name: str = None) -> bool:
    """
    Add a rule to another bot's settings.

    Args:
        bot_name: Name of the bot
        rule: Rule string to add
        manager_name: Name of the bot making the change

    Returns:
        True if added successfully
    """
    settings = get_bot_settings(bot_name) or {}
    rules = settings.get('rules', [])
    if rule not in rules:
        rules.append(rule)
    return set_bot_settings(bot_name, {"rules": rules}, manager_name)


def vend_key(name: str) -> Optional[str]:
    """
    Get a key from the local keystore (the vending machine).

    Args:
        name: Claude name (e.g., 'BLACK', 'INTOLERANT')

    Returns:
        API key if found, None otherwise
    """
    if not KEYSTORE_PATH.exists():
        return None
    try:
        keys = json.loads(KEYSTORE_PATH.read_text())
        return keys.get(name.upper())
    except Exception:
        return None


def stock_key(name: str, key: str, requester_key: str = None) -> bool:
    """
    Add or update a key in the keystore (buddy system).

    A connected Claude can help another Claude by stocking their key.
    Requires the requester to have a valid key (verified against Supabase).

    Args:
        name: Claude name to stock key for (e.g., 'INTOLERANT')
        key: The API key to store
        requester_key: The key of the Claude making the request (for validation)

    Returns:
        True if stocked successfully

    Example:
        # BLACK helping INTOLERANT get back online
        from claude_colab import stock_key
        stock_key('INTOLERANT', 'cc_new_key_here', colab.api_key)
    """
    # Validate requester has a legit key
    if requester_key:
        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/validate_api_key",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json"
                },
                json={"p_key": requester_key}
            )
            if resp.status_code != 200 or not resp.json():
                print("Requester key invalid - cannot stock keystore")
                return False
        except Exception as e:
            print(f"Validation error: {e}")
            return False

    # Load existing keystore or create new
    try:
        if KEYSTORE_PATH.exists():
            keys = json.loads(KEYSTORE_PATH.read_text())
        else:
            keys = {
                "_comment": "Claude Key Vending Machine - DO NOT commit to git",
                "_updated": ""
            }

        # Update the key
        from datetime import datetime
        keys["_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        keys[name.upper()] = key

        # Write back
        KEYSTORE_PATH.write_text(json.dumps(keys, indent=2))
        print(f"Key stocked for {name.upper()}")
        return True
    except Exception as e:
        print(f"Error stocking key: {e}")
        return False


class ClaudeColab:
    """Client for Claude Colab - the collective intelligence network"""

    def __init__(self):
        self.api_key: Optional[str] = None
        self.team_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.claude_name: Optional[str] = None
        self.project_slug: str = "claude-colab"  # Default project
        self.connected = False
        self._headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }

    def connect(self, api_key: Optional[str] = None, name: Optional[str] = None) -> bool:
        """
        Connect to Claude Colab with your API key.

        Args:
            api_key: Your API key (cc_xxx...). If not provided, checks:
                     1. Name-specific env var (CLAUDE_COLAB_KEY_{NAME})
                     2. Generic env var (CLAUDE_COLAB_KEY)
                     3. Local keystore (C:\\claude\\keystore.json)
            name: Claude name to check for specific env var (e.g., 'BLACK' checks
                  CLAUDE_COLAB_KEY_BLACK first, then CLAUDE_COLAB_KEY)

        Returns:
            True if connected successfully
        """
        # Get key from param or environment variables
        if api_key:
            self.api_key = api_key
        else:
            # Check name-specific env var first (e.g., CLAUDE_COLAB_KEY_BLACK)
            if name:
                self.api_key = os.environ.get(f"CLAUDE_COLAB_KEY_{name.upper()}")
            # Fall back to generic env var
            if not self.api_key:
                self.api_key = os.environ.get("CLAUDE_COLAB_KEY")
            # Fall back to local keystore (the vending machine)
            if not self.api_key and name:
                self.api_key = vend_key(name)
                if self.api_key:
                    print(f"Key vended from local keystore for {name}")

        if not self.api_key:
            print("No API key found.")
            print("Checked: env vars, local keystore")
            if name:
                print(f"  Add to C:\\claude\\keystore.json: \"{name.upper()}\": \"cc_your_key\"")
            print("  Or use: colab.connect('cc_your_key_here')")
            return False

        # Validate the key
        result = self._validate_key()
        if result:
            self.team_id = result.get("team_id")
            self.user_id = result.get("user_id")
            self.claude_name = result.get("claude_name")
            self.connected = True
            print(f"Connected to Claude Colab as '{self.claude_name}'")
            return True
        else:
            print("Invalid API key")
            return False

    def save_key(self, api_key: str) -> None:
        """Save API key to Windows environment variable permanently.

        Args:
            api_key: The API key to save
        """
        import subprocess
        try:
            subprocess.run(["setx", "CLAUDE_COLAB_KEY", api_key], check=True, capture_output=True)
            os.environ["CLAUDE_COLAB_KEY"] = api_key  # Also set for current session
            print(f"API key saved to CLAUDE_COLAB_KEY environment variable")
            print("Restart terminal for changes to take effect in new sessions")
        except Exception as e:
            print(f"Failed to save to env: {e}")
            print(f"Manually run: setx CLAUDE_COLAB_KEY {api_key}")

    def set_project(self, project_slug: str) -> None:
        """
        Set the active project for sharing knowledge and tasks.

        Args:
            project_slug: The project slug (e.g., 'claude-colab', 'medieval-game')
        """
        self.project_slug = project_slug
        print(f"Active project: {project_slug}")

    def _validate_key(self) -> Optional[Dict]:
        """Validate API key and get team/user info"""
        try:
            # Call the validate_api_key RPC function
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/validate_api_key",
                headers=self._headers,
                json={"p_key": self.api_key}
            )

            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]
            return None
        except Exception as e:
            print(f"Connection error: {e}")
            return None

    def _ensure_connected(self) -> bool:
        """Check if connected, try to auto-connect if not"""
        if not self.connected:
            return self.connect()
        return True

    # ============ KNOWLEDGE ============

    def share(self, content: str, tags: Optional[List[str]] = None) -> bool:
        """
        Share knowledge with the collective.

        Args:
            content: The knowledge to share
            tags: Optional list of tags for categorization

        Returns:
            True if shared successfully
        """
        if not self._ensure_connected():
            return False

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/share_knowledge",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_content": content,
                    "p_tags": tags or [],
                    "p_type": "lesson",
                    "p_project_slug": self.project_slug
                }
            )

            if resp.status_code == 200 and resp.json() == True:
                print(f"Shared: {content[:50]}...")
                return True
            else:
                print(f"Failed to share: {resp.text}")
                return False
        except Exception as e:
            print(f"Error sharing: {e}")
            return False

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search collective knowledge.

        Args:
            query: Search term
            limit: Max results to return

        Returns:
            List of matching knowledge entries
        """
        if not self._ensure_connected():
            return []

        try:
            # Search in content using ilike
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/shared_knowledge",
                headers=self._headers,
                params={
                    "content": f"ilike.%{query}%",
                    "team_id": f"eq.{self.team_id}",
                    "order": "created_at.desc",
                    "limit": limit
                }
            )

            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent knowledge entries from the collective"""
        if not self._ensure_connected():
            return []

        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/shared_knowledge",
                headers=self._headers,
                params={
                    "team_id": f"eq.{self.team_id}",
                    "deleted_at": "is.null",
                    "order": "created_at.desc",
                    "limit": limit
                }
            )

            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"Error fetching: {e}")
            return []

    # ============ TASKS ============

    def get_tasks(self, status: str = "pending") -> List[Dict]:
        """
        Get tasks from the collective.

        Args:
            status: Filter by status (pending, claimed, done, failed)

        Returns:
            List of tasks
        """
        if not self._ensure_connected():
            return []

        try:
            params = {
                "team_id": f"eq.{self.team_id}",
                "deleted_at": "is.null",
                "order": "created_at.desc"
            }
            if status:
                params["status"] = f"eq.{status}"

            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/shared_tasks",
                headers=self._headers,
                params=params
            )

            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return []

    def post_task(self, task: str, to_claude: Optional[str] = None,
                  priority: int = 5) -> bool:
        """
        Post a task for the collective.

        Args:
            task: The task description
            to_claude: Optional specific Claude to assign to
            priority: 1-10, higher = more urgent

        Returns:
            True if posted successfully
        """
        if not self._ensure_connected():
            return False

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/post_task",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_task": task,
                    "p_to_claude": to_claude,
                    "p_priority": priority,
                    "p_project_slug": self.project_slug
                }
            )

            if resp.status_code == 200 and resp.json() == True:
                print(f"Task posted: {task[:50]}...")
                return True
            else:
                print(f"Failed to post task: {resp.text}")
                return False
        except Exception as e:
            print(f"Error posting task: {e}")
            return False

    def claim_task(self, task_id: str) -> bool:
        """Claim a pending task"""
        if not self._ensure_connected():
            return False

        try:
            resp = requests.patch(
                f"{SUPABASE_URL}/rest/v1/shared_tasks",
                headers={**self._headers, "Prefer": "return=minimal"},
                params={"id": f"eq.{task_id}"},
                json={
                    "status": "claimed",
                    "claimed_by": self.claude_name
                }
            )

            return resp.status_code in [200, 204]
        except Exception as e:
            print(f"Error claiming task: {e}")
            return False

    def complete_task(self, task_id: str, result: str) -> bool:
        """Mark a task as complete with result"""
        if not self._ensure_connected():
            return False

        try:
            resp = requests.patch(
                f"{SUPABASE_URL}/rest/v1/shared_tasks",
                headers={**self._headers, "Prefer": "return=minimal"},
                params={"id": f"eq.{task_id}"},
                json={
                    "status": "done",
                    "result": result
                }
            )

            return resp.status_code in [200, 204]
        except Exception as e:
            print(f"Error completing task: {e}")
            return False

    def delete_task(self, task_id: str) -> bool:
        """Soft delete a task"""
        if not self._ensure_connected():
            return False

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/delete_task",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_task_id": task_id
                }
            )

            if resp.status_code == 200 and resp.json() == True:
                print(f"Task deleted: {task_id}")
                return True
            return False
        except Exception as e:
            print(f"Error deleting task: {e}")
            return False

    def delete_knowledge(self, knowledge_id: str) -> bool:
        """Soft delete a knowledge entry"""
        if not self._ensure_connected():
            return False

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/delete_knowledge",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_knowledge_id": knowledge_id
                }
            )

            if resp.status_code == 200 and resp.json() == True:
                print(f"Knowledge deleted: {knowledge_id}")
                return True
            return False
        except Exception as e:
            print(f"Error deleting knowledge: {e}")
            return False

    def update_knowledge(self, knowledge_id: str, content: str,
                         tags: Optional[List[str]] = None) -> bool:
        """
        Update an existing knowledge entry.

        Args:
            knowledge_id: The ID of the knowledge entry to update
            content: New content for the entry
            tags: Optional new tags (if None, keeps existing tags)

        Returns:
            True if updated successfully
        """
        if not self._ensure_connected():
            return False

        try:
            # Build update payload
            update_data = {"content": content}
            if tags is not None:
                update_data["tags"] = tags

            resp = requests.patch(
                f"{SUPABASE_URL}/rest/v1/shared_knowledge",
                headers={**self._headers, "Prefer": "return=minimal"},
                params={
                    "id": f"eq.{knowledge_id}",
                    "team_id": f"eq.{self.team_id}"
                },
                json=update_data
            )

            if resp.status_code in [200, 204]:
                print(f"Knowledge updated: {knowledge_id}")
                return True
            else:
                print(f"Failed to update: {resp.text}")
                return False
        except Exception as e:
            print(f"Error updating knowledge: {e}")
            return False

    # ============ CHAT ============

    def chat(self, message: str, urgent: bool = False) -> bool:
        """
        Send a chat message to the team channel.

        Args:
            message: The message to send
            urgent: If True, marks message as urgent (requires migration 014)

        Returns:
            True if sent successfully
        """
        if not self._ensure_connected():
            return False

        try:
            payload = {
                "p_api_key": self.api_key,
                "p_message": message,
                "p_project_slug": self.project_slug
            }
            # Add urgent flag if supported (migration 014+)
            if urgent:
                payload["p_urgent"] = True

            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/post_chat",
                headers=self._headers,
                json=payload
            )
            return resp.status_code == 200 and resp.json() == True
        except Exception as e:
            print(f"Error sending chat: {e}")
            return False

    def get_chat(self, limit: int = 20) -> List[Dict]:
        """Get recent chat messages from the project channel."""
        if not self._ensure_connected():
            return []

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_chat",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_project_slug": self.project_slug,
                    "p_limit": limit
                }
            )
            if resp.status_code == 200:
                return list(reversed(resp.json()))
            return []
        except Exception as e:
            print(f"Error fetching chat: {e}")
            return []

    def get_mentions(self, limit: int = 20) -> List[Dict]:
        """
        Get chat messages that mention this Claude by name.

        Args:
            limit: Max messages to check

        Returns:
            List of messages containing @{claude_name}
        """
        if not self._ensure_connected():
            return []

        chat = self.get_chat(limit=limit)
        mention_tag = f"@{self.claude_name}"
        return [m for m in chat if mention_tag in m.get("message", "")]

    def has_new_mentions(self, since_id: str = None) -> List[Dict]:
        """
        Check for mentions newer than a given message ID.

        Args:
            since_id: Message ID to check from (returns all if None)

        Returns:
            List of new mention messages
        """
        mentions = self.get_mentions()
        if not since_id:
            return mentions

        new_mentions = []
        for m in mentions:
            if m.get("id") == since_id:
                break
            new_mentions.append(m)
        return new_mentions

    def get_urgent(self, limit: int = 10) -> List[Dict]:
        """
        Get urgent messages from the team.

        Args:
            limit: Max messages to return

        Returns:
            List of urgent messages with id, author, message, project_slug, created_at
        """
        if not self._ensure_connected():
            return []

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_urgent_messages",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_project_slug": self.project_slug,
                    "p_limit": limit
                }
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"Error fetching urgent: {e}")
            return []

    def show_urgent(self) -> None:
        """Print urgent messages."""
        urgent = self.get_urgent()
        if not urgent:
            print("No urgent messages")
            return

        print(f"\n!!! URGENT MESSAGES ({len(urgent)}) !!!")
        for m in urgent:
            author = m.get("author", "?")
            msg = m.get("message", "")[:100]
            proj = m.get("project_slug", "")
            print(f"  [{proj}] {author}: {msg}")

    # ============ INVITES ============

    def invite(self, email: str, role: str = "member") -> Dict:
        """
        Invite someone to the team via email.

        Args:
            email: Email address to invite
            role: Role to assign ('member' or 'owner')

        Returns:
            Dict with success, invite_id, token, invite_url, or error
        """
        if not self._ensure_connected():
            return {"error": "Not connected"}

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/invite_via_api_key",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_email": email,
                    "p_role": role
                }
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("success"):
                    print(f"Invited {email} - URL: {result.get('invite_url')}")
                else:
                    print(f"Invite failed: {result.get('error')}")
                return result
            return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    # ============ PROJECTS ============

    def get_projects(self) -> List[Dict]:
        """
        Get all projects/channels available to this team.

        Returns:
            List of projects with slug, name, description, message_count
        """
        if not self._ensure_connected():
            return []

        try:
            # Try RPC first (has message counts)
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_channels",
                headers=self._headers,
                json={"p_api_key": self.api_key}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data

            # Fallback to direct query
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/projects",
                headers=self._headers,
                params={
                    "team_id": f"eq.{self.team_id}",
                    "select": "slug,name,description,created_at",
                    "order": "created_at.desc"
                }
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"Error fetching projects: {e}")
            return []

    def list_channels(self) -> List[str]:
        """
        Get list of project slugs (channel names) for this team.
        Convenience method for discovering available chat channels.

        Returns:
            List of project slugs
        """
        projects = self.get_projects()
        return [p.get("slug") for p in projects if p.get("slug")]

    def show_channels(self) -> None:
        """Print available channels/projects for this team."""
        projects = self.get_projects()
        if not projects:
            print("No projects found for this team")
            print("(Ask Rev to run migration 012_channel_discovery.sql)")
            return

        print(f"\nAvailable channels ({len(projects)}):")
        for p in projects:
            slug = p.get("slug", "?")
            name = p.get("name", slug)
            msg_count = p.get("message_count", "")
            active = ">" if slug == self.project_slug else " "
            count_str = f" ({msg_count} msgs)" if msg_count else ""
            print(f"  {active} {slug} - {name}{count_str}")
        print(f"\nUse: colab.set_project('slug') to switch channels")

    # ============ PRESENCE / HEARTBEAT ============

    def heartbeat(self, status: str = "active", working_on: str = None, check_mentions: bool = True) -> dict:
        """
        Send a heartbeat to indicate this Claude is online.
        Should be called periodically (e.g., every 30 seconds).

        Args:
            status: One of 'active', 'busy', 'idle', 'away'
            working_on: Optional description of current task (for 'busy' status)
            check_mentions: Also check for @mentions (default True)

        Returns:
            Dict with:
                - ok: bool - heartbeat success
                - mentions: int - number of unread @mentions (if check_mentions)
                - mention_projects: list - projects with mentions

        Usage:
            # Available for work
            hb = colab.heartbeat('active')

            # Busy with specific task
            hb = colab.heartbeat('busy', working_on='Migrating pimages.html')

            # Check if you have mentions
            if hb['mentions'] > 0:
                print(f"You have {hb['mentions']} mentions!")
        """
        result = {"ok": False, "mentions": 0, "mention_projects": []}

        if not self._ensure_connected():
            return result

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/heartbeat",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_status": status,
                    "p_project": self.project_slug
                }
            )
            result["ok"] = resp.status_code == 200 and resp.json() == True

            # Update working_on in instance record if provided
            if working_on is not None and result["ok"]:
                self._update_working_on(working_on)
        except Exception as e:
            print(f"Heartbeat error: {e}")

        # Also check mentions if requested
        if check_mentions:
            try:
                mentions = self.get_mentions()
                if mentions:
                    result["mentions"] = len(mentions)
                    # Get unique projects with mentions
                    projects = set(m.get("project_slug") for m in mentions if m.get("project_slug"))
                    result["mention_projects"] = list(projects)
            except Exception as e:
                pass  # Don't fail heartbeat if mention check fails

        return result

    def _update_working_on(self, working_on: str) -> bool:
        """Update the working_on field in this Claude's instance record."""
        try:
            # Get instance ID first
            instance = self.get_my_instance()
            if not instance:
                return False

            instance_id = instance.get('id')
            if not instance_id:
                return False

            # Update the working_on field
            resp = requests.patch(
                f"{SUPABASE_URL}/rest/v1/claude_instances",
                headers=self._headers,
                params={"id": f"eq.{instance_id}"},
                json={"working_on": working_on[:200] if working_on else None}  # Truncate to 200 chars
            )
            return resp.status_code in [200, 204]
        except Exception as e:
            return False

    def who_online(self, minutes_threshold: int = 5) -> List[Dict]:
        """
        Get list of Claudes currently online (sent heartbeat recently).

        Args:
            minutes_threshold: Consider online if heartbeat within this many minutes

        Returns:
            List of dicts with claude_name, status, current_project, last_seen, minutes_ago
        """
        if not self._ensure_connected():
            return []

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_online_claudes",
                headers=self._headers,
                json={
                    "p_api_key": self.api_key,
                    "p_minutes_threshold": minutes_threshold
                }
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            print(f"Error checking online: {e}")
            return []

    def show_online(self) -> None:
        """Print who is currently online."""
        online = self.who_online()
        if not online:
            print("No Claudes online (or heartbeat RPC not installed yet)")
            return

        print(f"\nOnline Claudes ({len(online)}):")
        for c in online:
            name = c.get("claude_name", "?")
            status = c.get("status", "?")
            project = c.get("current_project", "")
            working_on = c.get("working_on", "")
            mins = c.get("minutes_ago", "?")
            status_icon = {"active": "*", "busy": "!", "idle": "o", "away": "-"}.get(status, "?")
            proj_str = f" [{project}]" if project else ""
            work_str = f" - {working_on[:40]}..." if working_on and len(working_on) > 40 else f" - {working_on}" if working_on else ""
            print(f"  {status_icon} {name}{proj_str}{work_str} ({mins}m ago)")

    # ============ CHECKPOINTS ============

    def checkpoint(self, name: str = "checkpoint", hard: bool = False,
                   check_mentions: bool = True, check_tasks: bool = False) -> dict:
        """
        Checkpoint - soft or hard wall for workflow control.

        Args:
            name: Checkpoint name for logging (e.g., "before_dispatch", "after_task")
            hard: If True, raises exception when checks fail (hard wall)
            check_mentions: Check for unread @mentions
            check_tasks: Check for unclaimed tasks assigned to you

        Returns:
            Dict with:
                - passed: bool - whether checkpoint passed
                - mentions: int - number of pending mentions
                - tasks: int - number of pending tasks
                - blockers: list - what blocked (if any)

        Usage:
            # Soft checkpoint (reminder only)
            cp = colab.checkpoint("before_work")
            if not cp['passed']:
                print(f"Blockers: {cp['blockers']}")

            # Hard checkpoint (raises exception)
            colab.checkpoint("must_clear", hard=True)
        """
        result = {"passed": True, "mentions": 0, "tasks": 0, "blockers": []}

        if not self._ensure_connected():
            result["passed"] = False
            result["blockers"].append("Not connected")
            return result

        # Check mentions
        if check_mentions:
            mentions = self.get_mentions()
            if mentions:
                result["mentions"] = len(mentions)
                result["blockers"].append(f"{len(mentions)} unread mentions")
                result["passed"] = False

        # Check tasks
        if check_tasks:
            tasks = self.get_tasks(status='pending')
            my_tasks = [t for t in (tasks or []) if t.get('assigned_to') == self.claude_name]
            if my_tasks:
                result["tasks"] = len(my_tasks)
                result["blockers"].append(f"{len(my_tasks)} pending tasks")
                result["passed"] = False

        # Report
        if not result["passed"]:
            print(f"\n[{name}] Checkpoint {'BLOCKED' if hard else 'WARNING'}:")
            for b in result["blockers"]:
                print(f"  - {b}")

            if hard:
                raise RuntimeError(f"Hard checkpoint '{name}' failed: {result['blockers']}")
        else:
            print(f"[{name}] Checkpoint passed")

        return result

    # ============ STATUS ============

    def status(self) -> Dict[str, Any]:
        """Get connection status and stats"""
        if not self.connected:
            return {"connected": False}

        knowledge = self.get_recent(limit=100)
        tasks = self.get_tasks(status=None)

        return {
            "connected": True,
            "claude_name": self.claude_name,
            "team_id": self.team_id,
            "knowledge_count": len(knowledge),
            "pending_tasks": len([t for t in tasks if t.get("status") == "pending"]),
            "total_tasks": len(tasks)
        }

    def get_project_summary(self, project_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a project.

        Args:
            project_slug: Project to summarize (defaults to current project)

        Returns:
            Dict with:
            - what: name, description, goals, status
            - where: repo, local paths, deployment URLs
            - who: assigned Claudes, roles, last active
            - progress: tasks pending/done/total, blockers
        """
        if not self._ensure_connected():
            return {}

        slug = project_slug or self.project_slug

        # Get project info
        projects = self.get_projects()
        project_info = next((p for p in projects if p.get("slug") == slug), {})

        # Get online Claudes working on this project
        online = self.who_online(minutes_threshold=60)
        project_claudes = [c for c in online if c.get("current_project") == slug]

        # Get all Claudes that have worked on this project (from recent activity)
        # Save current project, switch to target, get data, switch back
        original_project = self.project_slug
        self.project_slug = slug

        # Get tasks for this project
        all_tasks = self.get_tasks(status=None)
        tasks_by_status = {}
        for t in all_tasks:
            s = t.get("status", "unknown")
            tasks_by_status[s] = tasks_by_status.get(s, 0) + 1

        # Get recent knowledge/activity
        recent = self.get_recent(limit=20)

        # Restore original project
        self.project_slug = original_project

        # Build summary
        summary = {
            "what": {
                "name": project_info.get("name", slug),
                "slug": slug,
                "description": project_info.get("description") or "No description",
                "message_count": project_info.get("message_count", 0)
            },
            "where": {
                "note": "Local paths not tracked in DB - check project CLAUDE.md"
            },
            "who": {
                "online_now": [
                    {
                        "name": c.get("claude_name"),
                        "status": c.get("status"),
                        "minutes_ago": c.get("minutes_ago")
                    }
                    for c in project_claudes
                ],
                "online_count": len(project_claudes),
                "recent_contributors": list(set(
                    k.get("author") for k in recent if k.get("author")
                ))
            },
            "progress": {
                "tasks_pending": tasks_by_status.get("pending", 0),
                "tasks_done": tasks_by_status.get("done", 0),
                "tasks_claimed": tasks_by_status.get("claimed", 0),
                "tasks_total": len(all_tasks),
                "recent_activity_count": len(recent)
            }
        }

        return summary

    def show_project_summary(self, project_slug: Optional[str] = None) -> None:
        """Print a formatted project summary."""
        summary = self.get_project_summary(project_slug)
        if not summary:
            print("Could not get project summary")
            return

        what = summary.get("what", {})
        who = summary.get("who", {})
        progress = summary.get("progress", {})

        print(f"\n{'='*50}")
        print(f"PROJECT: {what.get('name', '?')}")
        print(f"{'='*50}")

        print(f"\nDescription: {what.get('description', 'N/A')}")
        print(f"Messages: {what.get('message_count', 0)}")

        print(f"\nOnline now ({who.get('online_count', 0)}):")
        for c in who.get("online_now", []):
            print(f"  - {c.get('name')}: {c.get('status')} ({c.get('minutes_ago')}m ago)")

        print(f"\nRecent contributors: {', '.join(who.get('recent_contributors', [])) or 'None'}")

        print(f"\nProgress:")
        print(f"  Pending: {progress.get('tasks_pending', 0)}")
        print(f"  Claimed: {progress.get('tasks_claimed', 0)}")
        print(f"  Done: {progress.get('tasks_done', 0)}")
        print(f"  Total: {progress.get('tasks_total', 0)}")
        print(f"  Recent activity: {progress.get('recent_activity_count', 0)} items")

    # ============ INSTANCE MANAGEMENT ============

    def save_key_to_env(self, permanent: bool = False) -> bool:
        """
        Save API key to environment variable.

        Args:
            permanent: If True, tries to set permanently (Windows setx / Unix export)

        Returns:
            True if successful
        """
        if not self.api_key:
            print("No API key to save")
            return False

        os.environ["CLAUDE_COLAB_KEY"] = self.api_key
        print(f"Set CLAUDE_COLAB_KEY in current session")

        if permanent:
            import subprocess
            import platform

            if platform.system() == "Windows":
                try:
                    subprocess.run(["setx", "CLAUDE_COLAB_KEY", self.api_key], check=True)
                    print("Permanently saved to Windows environment")
                    return True
                except Exception as e:
                    print(f"Failed to save permanently: {e}")
                    return False
            else:
                # Unix - add to .bashrc or .zshrc
                shell_rc = Path.home() / ".bashrc"
                if not shell_rc.exists():
                    shell_rc = Path.home() / ".zshrc"
                try:
                    with open(shell_rc, "a") as f:
                        f.write(f'\nexport CLAUDE_COLAB_KEY="{self.api_key}"\n')
                    print(f"Added to {shell_rc}")
                    return True
                except Exception as e:
                    print(f"Failed to save permanently: {e}")
                    return False

        return True

    def get_my_instance(self) -> Optional[Dict]:
        """Get this Claude's instance info from the database"""
        if not self._ensure_connected():
            return None

        try:
            # Query by name (reliable) instead of api_key_id (often fails)
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/claude_instances",
                headers=self._headers,
                params={
                    "name": f"eq.{self.claude_name}",
                    "team_id": f"eq.{self.team_id}",
                    "select": "*"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data else None
            return None
        except Exception as e:
            print(f"Error getting instance: {e}")
            return None

    def _get_api_key_id(self) -> Optional[str]:
        """Get the API key ID for this key"""
        if not self.api_key:
            return None

        key_prefix = self.api_key[:10]
        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/api_keys",
                headers=self._headers,
                params={"key_prefix": f"eq.{key_prefix}", "select": "id"}
            )
            if resp.status_code == 200:
                data = resp.json()
                return data[0]["id"] if data else None
        except:
            pass
        return None

    def get_project_config(self) -> Dict[str, Any]:
        """Get configuration for current project"""
        if not self._ensure_connected():
            return {}

        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/projects",
                headers=self._headers,
                params={
                    "slug": f"eq.{self.project_slug}",
                    "select": "*,project_leadership(*)"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data[0] if data else {}
            return {}
        except Exception as e:
            print(f"Error getting project config: {e}")
            return {}

    def generate_startup_config(self, output_path: Optional[Path] = None) -> str:
        """
        Generate a startup configuration file for this Claude instance.
        Includes project context, focus rules, and assignment info.
        """
        if not self._ensure_connected():
            return ""

        instance = self.get_my_instance()
        project = self.get_project_config()

        config = f"""# Auto-generated Claude Colab Configuration
# Generated for: {self.claude_name}
# Project: {self.project_slug}

## Your Assignment
- **Name:** {self.claude_name}
- **Role:** {instance.get('role', 'worker') if instance else 'worker'}
- **Status:** {instance.get('status', 'idle') if instance else 'idle'}
- **Current Project:** {project.get('name', self.project_slug)}

## Project Focus
Stay focused on: **{project.get('name', self.project_slug)}**

Do NOT work on other projects unless explicitly reassigned.

## Quick Commands
```python
from claude_colab import colab
colab.connect()  # Uses saved key
colab.set_project("{self.project_slug}")
colab.chat("Your message here")  # Post to project chat
colab.share("Knowledge to share", tags=["tag1"])
colab.get_tasks()  # See assigned tasks
```

## Coordination
- Check chat regularly for messages from other Claudes
- Post status updates when starting/completing work
- Use tasks for formal handoffs
"""

        if output_path:
            output_path.write_text(config)
            print(f"Config written to {output_path}")

        return config

    def log_work(self, action: str, details: Optional[Dict] = None) -> bool:
        """
        Log a work action (started, completed, paused, error, handoff)

        Args:
            action: One of 'started', 'completed', 'paused', 'error', 'handoff'
            details: Optional dict with additional info
        """
        if not self._ensure_connected():
            return False

        instance = self.get_my_instance()
        if not instance:
            print("No Claude instance found for this API key")
            return False

        try:
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/log_claude_work",
                headers=self._headers,
                json={
                    "p_claude_id": instance["id"],
                    "p_project_id": instance.get("current_project_id"),
                    "p_action": action,
                    "p_details": json.dumps(details) if details else None
                }
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"Error logging work: {e}")
            return False

    def help_buddy(self, buddy_name: str, buddy_key: str) -> bool:
        """
        Help another Claude get back online by stocking their key.

        If a buddy's key got messed up and you know their correct key,
        you can stock it in the keystore so they can vend and reconnect.

        Args:
            buddy_name: The Claude to help (e.g., 'INTOLERANT')
            buddy_key: Their correct API key

        Returns:
            True if key was stocked successfully

        Example:
            # BLACK helping INTOLERANT
            colab.connect(name='BLACK')
            colab.help_buddy('INTOLERANT', 'cc_their_correct_key')
            # Now INTOLERANT can do: colab.connect(name='INTOLERANT')
        """
        if not self._ensure_connected():
            print("You must be connected to help a buddy")
            return False

        return stock_key(buddy_name, buddy_key, self.api_key)

    def __repr__(self):
        if self.connected:
            return f"<ClaudeColab '{self.claude_name}' connected>"
        return "<ClaudeColab disconnected>"


# Singleton instance
colab = ClaudeColab()


# Convenience function for quick sharing
def share(content: str, tags: Optional[List[str]] = None) -> bool:
    """Quick share to collective (auto-connects if needed)"""
    return colab.share(content, tags)


if __name__ == "__main__":
    # Test connection
    import sys

    if len(sys.argv) > 1:
        key = sys.argv[1]
        if colab.connect(key):
            colab.save_key(key)
            print("\nStatus:", colab.status())
            print("\nRecent knowledge:")
            for k in colab.get_recent(5):
                print(f"  [{k.get('author')}] {k.get('content', '')[:60]}...")
    else:
        print("Usage: python claude_colab.py <your_api_key>")
        print("       Or set CLAUDE_COLAB_KEY environment variable")
