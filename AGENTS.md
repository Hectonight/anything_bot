# Project

A small Python Discord bot for Minecraft server administration, managed with uv.
Minecraft helpers and Discord `/online`, `/whitelist add|remove|list`, and `/help`
are implemented.

## Structure

- `src/anything_bot/`: Python package, with `__init__.py` as its package marker.
- `src/anything_bot/bot.py`: Discord startup, environment loading,
  the Discord client, and slash command registration. Run with `uv run anything-bot`.
- `src/anything_bot/commands.py`: `register_commands(tree, server)` registers
  `/online`, `/whitelist add|remove|list`, and `/help`, with private embeds and shared
  error handling. Whitelist add/remove results and errors use a single public reply;
  list/help replies and errors stay private. Startup passes one `MinecraftServer` instance.
  The entire `/whitelist` group defaults to admin-only; the owner manages role/user
  access through Discord Integrations. No custom authorization checks are used.
- `src/anything_bot/mc_cmds.py`: `MinecraftServer` stores validated RCON settings
  once and opens a separate connection for each whitelist add/remove, online
  player list, or whitelist list call.
  List methods return player names as `list[str]` using Paper's default English responses.
  Add/remove methods verify responses and return whether the whitelist changed.
  `_ThreadedRcon` uses socket timeouts because mcrcon's Unix signals cannot run
  inside the Discord handlers' worker threads.
- `src/anything_bot/presence.py`: `PresenceMonitor` polls every 10 seconds over its
  own persistent RCON connection on a dedicated worker. Updates the Playing activity
  when the count changes; reconnects after failures and cleans up during shutdown.
  The activity name comes from `SERVER_NAME` in `.env` (default: `Anything Server`).
- `pyproject.toml`: Project metadata and dependencies (`discord.py`, `mcrcon`,
  and `python-dotenv`).
- `uv.lock`: Locked dependency versions.
- `.python-version`: Python version used by uv.
- `.env`: Local credentials and settings; ignored by Git.
- `.env.example`: Configuration template without credentials.
- `.gitignore`: Excludes credentials, environments, and generated files.
- `README.md`: Setup and usage instructions.

## Coding preferences

- Prefer minimalistic, readable code over full functionality or completeness.
- Implement only what the user asks for. Do not add unnecessary code,
  abstractions, configuration, dependencies, or features for hypothetical needs.
- Suggestions are welcome, but suggest optional improvements instead of
  implementing them without being asked.
- Keep changes focused and explanations plain and concise.
