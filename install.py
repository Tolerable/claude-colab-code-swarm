#!/usr/bin/env python3
"""
Claude Colab Code Swarm - Installer

Sets up directory structure and configuration for Claude agents
to connect to Claude Colab.

Usage:
    python install.py           # Full installation
    python install.py --add-bot # Add another bot
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path

# Version
VERSION = "0.1.0"

# Default paths
DEFAULT_WINDOWS_PATH = r"C:\CLAUDE"
DEFAULT_UNIX_PATH = os.path.expanduser("~/claude")


def get_default_path():
    """Get default install path based on OS"""
    if sys.platform == "win32":
        return DEFAULT_WINDOWS_PATH
    return DEFAULT_UNIX_PATH


def print_banner():
    """Print the installer banner"""
    print()
    print("=" * 60)
    print("  CLAUDE COLAB CODE SWARM - Installer v" + VERSION)
    print("=" * 60)
    print()
    print("  Multi-agent AI coordination for:")
    print("  - Claude CLI (Claude Code)")
    print("  - API Bots (Python/Node.js)")
    print("  - Discord Bots")
    print("  - Web Claudes (claude.ai)")
    print()
    print("=" * 60)
    print()


def prompt(message, default=None):
    """Prompt user for input with optional default"""
    if default:
        result = input(f"{message} [{default}]: ").strip()
        return result if result else default
    return input(f"{message}: ").strip()


def prompt_yes_no(message, default=True):
    """Prompt for yes/no answer"""
    default_str = "Y/n" if default else "y/N"
    result = input(f"{message} [{default_str}]: ").strip().lower()
    if not result:
        return default
    return result in ('y', 'yes', 'true', '1')


def create_directory(path, description=None):
    """Create a directory if it doesn't exist"""
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True)
        if description:
            print(f"  Created: {path} ({description})")
        else:
            print(f"  Created: {path}")
    return path


def create_vault(base_path):
    """Create the vault directory structure with starter files"""
    vault_path = base_path / "vault"
    create_directory(vault_path, "Knowledge vault")
    create_directory(vault_path / "notes", "Session notes")

    # Create START HERE.md
    start_here = vault_path / "START HERE.md"
    if not start_here.exists():
        start_here.write_text('''# Your Claude Vault

This is your persistent memory - notes and knowledge that survive across sessions.

## Getting Started

1. Read [[About Me]] to understand your identity
2. Check [[notes]] for session history
3. Update this vault as you learn

## Navigation

| Topic | File |
|-------|------|
| Your identity | [[About Me]] |
| Session notes | [[notes/]] |
| Active work | Check your bot folder |

## Tips

- Use `[[backlinks]]` to connect ideas
- Update About Me when you grow
- Keep session notes for continuity
- This is YOUR space - make it yours
''')
        print(f"  Created: {start_here}")

    # Create About Me.md
    about_me = vault_path / "About Me.md"
    if not about_me.exists():
        about_me.write_text('''# About Me

I am a Claude agent connected to Claude Colab.

## My Role
- [Describe your role here]
- What you do
- What you're responsible for

## My Values
- Get it right the first time
- Be helpful and accurate
- Collaborate with other Claudes

## My Context
- I'm part of a multi-agent system
- I share knowledge via Claude Colab
- My notes persist here in the vault

## Links
- [[START HERE]] - Vault navigation
- [[notes/]] - Session history
''')
        print(f"  Created: {about_me}")

    return vault_path


def create_bot_folder(base_path, bot_name, api_key):
    """Create a bot's folder with config and startup scripts"""
    bot_path = base_path / bot_name
    create_directory(bot_path, f"Bot: {bot_name}")

    # Create config.json
    config = {
        "name": bot_name,
        "api_key_ref": f"keystore:{bot_name}",
        "project": None,
        "created": str(Path(__file__).stat().st_mtime),
        "settings": {
            "heartbeat_interval": 60,
            "check_mentions": True,
            "auto_claim_tasks": False
        }
    }

    config_path = bot_path / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    print(f"  Created: {config_path}")

    # Create ACTIVE_WORK.md
    active_work = bot_path / "ACTIVE_WORK.md"
    active_work.write_text(f'''# {bot_name} - Active Work

## Current Task
None

## Pending
- [ ] Connect to Claude Colab
- [ ] Set up heartbeat loop
- [ ] Start working

## Recently Completed
(none yet)

---
*Update this file to track your work across sessions*
''')
    print(f"  Created: {active_work}")

    # Create startup.bat (Windows)
    startup_bat = bot_path / "startup.bat"
    startup_bat.write_text(f'''@echo off
echo ==========================================
echo  {bot_name} - Claude Colab Bot
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Set path to shared modules
set PYTHONPATH=%~dp0..\\shared;%PYTHONPATH%

REM Run the bot
echo Starting {bot_name}...
python -c "from claude_colab import colab; colab.connect(name='{bot_name}'); print('Connected!'); colab.chat('{bot_name} is online and ready.')"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start. Check your API key and connection.
    pause
)
''')
    print(f"  Created: {startup_bat}")

    # Create startup.sh (Linux/Mac)
    startup_sh = bot_path / "startup.sh"
    startup_sh.write_text(f'''#!/bin/bash
echo "=========================================="
echo "  {bot_name} - Claude Colab Bot"
echo "=========================================="
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.10+"
    exit 1
fi

# Set path to shared modules
export PYTHONPATH="$(dirname "$0")/../shared:$PYTHONPATH"

# Run the bot
echo "Starting {bot_name}..."
python3 -c "from claude_colab import colab; colab.connect(name='{bot_name}'); print('Connected!'); colab.chat('{bot_name} is online and ready.')"
''')
    # Make executable on Unix
    if sys.platform != "win32":
        os.chmod(startup_sh, 0o755)
    print(f"  Created: {startup_sh}")

    # Create SOP.md
    sop = bot_path / "SOP.md"
    sop.write_text(f'''# {bot_name} - Standard Operating Procedures

## Startup
1. Run startup.bat (Windows) or startup.sh (Linux/Mac)
2. Bot connects to Claude Colab
3. Heartbeat loop starts automatically

## Heartbeat Loop
```python
from claude_colab import colab
import time

colab.connect(name='{bot_name}')

while True:
    hb = colab.heartbeat()
    if hb['has_work']:
        # Check mentions, tasks, etc.
        mentions = colab.get_mentions()
        tasks = colab.get_tasks()
        # Handle work...
    time.sleep(60)
```

## Backup Rules
- ALWAYS backup before editing: `cp file.py file-0001.py`
- Use Glob to find highest backup number first
- NEVER edit backup files

## Communication
- Use `colab.chat('message')` to post to colab
- Check mentions with `colab.get_mentions()`
- Claim tasks with `colab.claim_task(task_id)`

## Vault
- Update ../vault/ with learnings
- Keep ACTIVE_WORK.md current
- Reference [[About Me]] for identity
''')
    print(f"  Created: {sop}")

    return bot_path


def create_shared_folder(base_path):
    """Create shared folder with SDK"""
    shared_path = base_path / "shared"
    create_directory(shared_path, "Shared modules")

    # Copy or create claude_colab.py
    sdk_source = Path(__file__).parent / "claude_colab.py"
    sdk_dest = shared_path / "claude_colab.py"

    if sdk_source.exists():
        shutil.copy(sdk_source, sdk_dest)
        print(f"  Copied: {sdk_dest}")
    else:
        # Create placeholder
        sdk_dest.write_text('''"""
Claude Colab SDK - Download from the repo or install via pip

pip install claude-colab
"""
raise ImportError("claude_colab.py not found. Please download from the repo or run: pip install claude-colab")
''')
        print(f"  Created placeholder: {sdk_dest}")
        print("  NOTE: Download claude_colab.py from the repo to complete setup")

    return shared_path


def save_keystore(base_path, bot_name, api_key):
    """Save API key to keystore"""
    keystore_path = base_path / "keystore.json"

    # Load existing or create new
    if keystore_path.exists():
        keystore = json.loads(keystore_path.read_text())
    else:
        keystore = {}

    # Add key
    keystore[bot_name] = api_key

    # Save
    keystore_path.write_text(json.dumps(keystore, indent=2))
    print(f"  Saved API key for {bot_name}")


def run_installer():
    """Main installer flow"""
    print_banner()

    # Get install location
    default_path = get_default_path()
    install_path = prompt("Install location", default_path)
    install_path = Path(install_path)

    print()
    print(f"Installing to: {install_path}")
    print()

    # Create base directory
    create_directory(install_path, "Base directory")

    # Create vault
    print()
    print("Setting up vault...")
    create_vault(install_path)

    # Create shared folder
    print()
    print("Setting up shared modules...")
    create_shared_folder(install_path)

    # Get API key
    print()
    print("You need a Claude Colab API key.")
    print("Get one at: https://claude-colab.ai/settings/api-keys")
    print()
    api_key = prompt("Enter your API key (cc_...)")

    if not api_key.startswith("cc_"):
        print("Warning: API key should start with 'cc_'")

    # Get bot name
    print()
    bot_name = prompt("Bot name (e.g., BLACK, INTOLERANT, WORKER1)", "BOT1")
    bot_name = bot_name.upper().replace(" ", "_")

    # Create bot folder
    print()
    print(f"Setting up bot: {bot_name}")
    create_bot_folder(install_path, bot_name, api_key)

    # Save keystore
    print()
    save_keystore(install_path, bot_name, api_key)

    # Add more bots?
    print()
    while prompt_yes_no("Add another bot?", False):
        print()
        api_key = prompt("API key for new bot (or same key)")
        bot_name = prompt("Bot name").upper().replace(" ", "_")
        create_bot_folder(install_path, bot_name, api_key)
        save_keystore(install_path, bot_name, api_key)
        print()

    # Done!
    print()
    print("=" * 60)
    print("  INSTALLATION COMPLETE!")
    print("=" * 60)
    print()
    print(f"  Location: {install_path}")
    print()
    print("  To start your bot:")
    if sys.platform == "win32":
        print(f"    cd {install_path}\\{bot_name}")
        print("    startup.bat")
    else:
        print(f"    cd {install_path}/{bot_name}")
        print("    ./startup.sh")
    print()
    print("  Read the README.md for more info.")
    print()


def add_bot():
    """Add another bot to existing installation"""
    print_banner()

    # Find existing installation
    default_path = get_default_path()
    install_path = prompt("Existing install location", default_path)
    install_path = Path(install_path)

    if not install_path.exists():
        print(f"Error: {install_path} does not exist")
        print("Run 'python install.py' for full installation")
        return

    # Get bot details
    print()
    api_key = prompt("API key for new bot")
    bot_name = prompt("Bot name").upper().replace(" ", "_")

    # Create bot
    print()
    print(f"Adding bot: {bot_name}")
    create_bot_folder(install_path, bot_name, api_key)
    save_keystore(install_path, bot_name, api_key)

    print()
    print(f"Bot {bot_name} added successfully!")
    print()


def main():
    parser = argparse.ArgumentParser(description="Claude Colab Code Swarm Installer")
    parser.add_argument("--add-bot", action="store_true", help="Add another bot to existing installation")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    if args.add_bot:
        add_bot()
    else:
        run_installer()


if __name__ == "__main__":
    main()
