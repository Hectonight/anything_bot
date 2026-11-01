# Anything Bot

A Discord bot for managing a Minecraft Java/Paper server through RCON.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

1. Install dependencies:

   ```bash
   uv sync --locked
   ```

2. Copy `.env.example` to `.env` if you don't already have one. Fill in:

   ```dotenv
   DISCORD_TOKEN=your-bot-token
   SERVER_NAME=Anything Server
   RCON_HOST=127.0.0.1
   RCON_PORT=25575
   RCON_PASSWORD=your-rcon-password
   ```

   Use the Minecraft server's address for `RCON_HOST` if it runs elsewhere.
   Keep `.env` private; it is ignored by Git.

3. Enable RCON in Minecraft's `server.properties`, then restart the server:

   ```properties
   enable-rcon=true
   rcon.port=25575
   rcon.password=your-rcon-password
   ```

4. Create a bot in the [Discord Developer Portal](https://discord.com/developers/applications)
   and invite it with the `bot` and `applications.commands` scopes.
   No privileged intents are needed.

## Run

```bash
uv run anything-bot
```

Stop with Ctrl+C. Logs appear in the terminal. Commands register globally on startup.

The bot shows "Playing Anything Server" (configured by `SERVER_NAME`) with the player count in its activity
state, refreshed every 10 seconds
over its own persistent RCON connection. If the count cannot be retrieved, it shows
"player count unavailable" with an idle status and retries on the next refresh.

## Commands

| Command | Does |
| --- | --- |
| `/online` | Lists online players |
| `/whitelist list` | Lists whitelisted players |
| `/whitelist add username` | Adds a player |
| `/whitelist remove username` | Removes a player |
| `/help` | Shows command help |

Whitelist commands default to admin-only. The server owner can grant access under
**Server Settings → Integrations → your bot → Manage → /whitelist**.

Whitelist add/remove replies, including errors, are public. List/help replies are private.
Player names must be 3–16 letters, digits, or underscores. Response parsing assumes
Paper's default English messages.

## Code

All Python code is in `src/anything_bot/`:

- `bot.py` - startup, logging, and Discord connection.
- `commands.py` - slash commands and embeds.
- `mc_cmds.py` - Minecraft commands, validation, and RCON connections.
- `presence.py` - live player-count activity and its persistent RCON connection.
