"""Discord bot startup. Run with: uv run anything-bot"""

import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

from anything_bot.commands import register_commands
from anything_bot.mc_cmds import MinecraftServer

logger = logging.getLogger(__name__)

client = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(client)


@client.event
async def setup_hook() -> None:
    if not tree.get_commands():
        logger.info("No commands registered; skipping sync")
        return

    logger.info("Syncing global commands")
    try:
        synced = await tree.sync()
    except Exception:
        logger.exception("Command sync failed")
        raise
    logger.info("Synced %d top-level commands", len(synced))


@client.event
async def on_ready() -> None:
    logger.info("Connected as %s", client.user)


@client.event
async def on_disconnect() -> None:
    logger.info("Discord disconnected")


@client.event
async def on_resumed() -> None:
    logger.info("Discord session resumed")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting bot")
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        logger.error("DISCORD_TOKEN is missing")
        raise SystemExit("Set DISCORD_TOKEN in .env before starting the bot.")

    try:
        server = MinecraftServer()
        register_commands(tree, server)
        logger.info("Connecting to Discord")
        client.run(token, log_handler=None)
    except Exception:
        logger.exception("Bot failed")
        raise
    finally:
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
