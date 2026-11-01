# Anything Bot

A small Discord bot for Minecraft server administration. The Discord connection
and slash command registration are set up. Minecraft whitelist helpers are
implemented separately. Discord `/online`, `/whitelist add|remove|list`, and `/help`
are enabled.

## Setup

Requires uv and Python 3.12 or newer.

```bash
uv sync --locked
```

A local `.env` already exists. For a fresh clone, run `cp .env.example .env`.
Fill in `DISCORD_TOKEN` with your application's bot token from the
[Discord Developer Portal](https://discord.com/developers/applications).
Install the bot on your server with the `bot` and `applications.commands` scopes.
No privileged intents are needed.

Commands register globally for servers where the bot is installed.
Keep credentials in `.env`, which Git ignores.

## Run

```bash
uv run anything-bot
```

This connects to Discord. Stop with Ctrl+C.

Timestamped console logs cover startup/shutdown, Discord connection events,
command registration/sync, command requests and outcomes, and RCON operations.
Command requests include user, server, and channel IDs. Errors include failure
details; unexpected errors include tracebacks. RCON responses and embed counts
are logged at DEBUG level (normal startup uses INFO). Tokens and RCON passwords
are not logged.

The Python package lives in `src/anything_bot/`. Its `__init__.py` is just a
package marker; Discord code is in `src/anything_bot/bot.py`:

- `client` manages the Discord connection.
- `tree` holds slash command definitions.
- `setup_hook` tells Discord about the commands on startup using `tree.sync()`.
  It skips synchronization while there are no commands.
- `on_ready` logs when the bot connects.
- `main` loads `.env`, checks settings, and starts the bot.

## Discord commands

`src/anything_bot/commands.py` registers `/online` and `/whitelist list` at startup.
Both are server-only, require no custom authorization check, and reply privately
with an embed containing the player count and one name per line. Empty results
show "Nobody is online" or "The whitelist is empty". Long lists are split into
separate embeds at player boundaries.

`/help` shows the available commands in a private embed without contacting Minecraft.
It is server-only and requires no custom authorization check.

Startup constructs one `MinecraftServer`, so RCON settings must be configured
before starting the bot. Construction does not connect to Minecraft. Commands
defer their responses and use `asyncio.to_thread()` for Minecraft calls. Parsing
and connection errors receive private error embeds; Minecraft response errors show
the server's message directly. Unexpected errors are logged and get a generic embed.

`/whitelist add username` and `/whitelist remove username` run the Minecraft
operation in a worker thread and reply with a private embed.
Successful changes also post a public embed in the channel. Already/not-whitelisted
results and errors remain private.
They distinguish changes from players already whitelisted or not whitelisted.
The entire `/whitelist` group (`add`, `remove`, and `list`) defaults to admin-only.
The server owner can grant roles/users access under **Server Settings → Integrations
→ your bot → Manage → /whitelist**. Discord stores and enforces these permissions;
there is no custom authorization check or database. Administrators always retain
access. `/online` and `/help` remain unrestricted by default. Restart the bot to
sync the new defaults; existing permissions configured in Discord can override them.
Minecraft operations and username validation stay in `MinecraftServer`. RCON errors
do not trigger automatic retries because a command may have executed before the
connection failed.

## Minecraft command helpers

`src/anything_bot/mc_cmds.py` provides a `MinecraftServer` class with
`add_to_whitelist(username)`, `remove_from_whitelist(username)`,
`list_online_players()`, and `list_whitelist()` methods.
The add/remove methods accept standard Java usernames: 3–16
ASCII letters, digits, or underscores. Invalid names raise `ValueError` before
connecting; whitespace is rejected rather than trimmed.

Enable RCON on your Minecraft server and configure these values in `.env`:

| Variable | Value |
| --- | --- |
| `RCON_HOST` | Server address; defaults to `127.0.0.1` when unset |
| `RCON_PORT` | Integer from 1–65535; defaults to `25575` when unset |
| `RCON_PASSWORD` | Required password matching the server configuration |

The constructor loads `.env` once without overriding existing environment variables
and stores the host, port, and password. It requires a nonempty host and password
and validates the port without connecting or authenticating. To pick up changed
settings, recreate the instance or restart the bot; existing environment variables
still take precedence over `.env`.

Each method opens its own RCON connection with a five-second timeout, sends one
command, and closes the connection. No connection is shared between calls.
The add/remove methods verify Paper's default English responses and return `True`
when the player was added or removed. Add returns `False` if already whitelisted;
remove returns `False` if not whitelisted. Success responses must identify the
requested player (ignoring capitalization). Failed commands, such as an unknown
player, and unexpected responses raise `MinecraftResponseError` (a `ValueError`
subclass containing the server's response). Configuration errors also
raise `ValueError`; connection and authentication errors propagate to the caller.

The list methods return `list[str]` containing player names, or `[]` when empty.
They parse Paper's default English responses and raise `ValueError` for unexpected
formats or inconsistent player counts. Responses changed by plugins or localization
are not supported.

Example usage (calling this contacts Minecraft and changes its whitelist):

```python
from anything_bot.mc_cmds import MinecraftServer

server = MinecraftServer()  # Load and validate settings; no connection yet.
print(server.add_to_whitelist("Steve"))
print(server.remove_from_whitelist("Steve"))
print(server.list_online_players())  # e.g. ["Steve", "Alex"]
print(server.list_whitelist())       # e.g. ["Steve", "Alex", "Notch"]
```

In a future async Discord handler, use
`response = await asyncio.to_thread(server.add_to_whitelist, username)` with `import asyncio`
so the blocking RCON call does not block the bot's event loop.

Dependencies: `discord.py`, `mcrcon`, and `python-dotenv`. Commit `pyproject.toml`
and `uv.lock` to keep the dependency setup reproducible.
