"""Discord commands for Minecraft server administration."""

import asyncio
import logging

import discord
from discord import app_commands
from mcrcon import MCRconException

from anything_bot.mc_cmds import MinecraftServer

logger = logging.getLogger(__name__)


def register_commands(tree: app_commands.CommandTree, server: MinecraftServer) -> None:
    """Register Minecraft commands and their shared error handler."""

    @tree.command(name="online", description="Show online Minecraft players.")
    @app_commands.guild_only()
    async def online(interaction: discord.Interaction) -> None:
        """Defer privately, call server.list_online_players() in a thread, and show names or nobody online."""
        logger.info("/online requested: user=%s guild=%s channel=%s", interaction.user.id, interaction.guild_id, interaction.channel_id)
        await interaction.response.defer(ephemeral=True)
        players = await asyncio.to_thread(server.list_online_players)
        await _send_player_list(interaction, "Online Players", players, "Nobody is online")
        logger.info("/online completed: user=%s players=%d", interaction.user.id, len(players))

    whitelist = app_commands.Group(
        name="whitelist", description="Manage the Minecraft whitelist.", guild_only=True,
        default_permissions=discord.Permissions.none(),
    )

    @whitelist.command(name="list", description="Show whitelisted Minecraft players.")
    async def whitelist_list(interaction: discord.Interaction) -> None:
        """Defer privately, call server.list_whitelist() in a thread, and show names or an empty list."""
        logger.info("/whitelist list requested: user=%s guild=%s channel=%s", interaction.user.id, interaction.guild_id, interaction.channel_id)
        await interaction.response.defer(ephemeral=True)
        players = await asyncio.to_thread(server.list_whitelist)
        await _send_player_list(interaction, "Whitelisted Players", players, "The whitelist is empty")
        logger.info("/whitelist list completed: user=%s players=%d", interaction.user.id, len(players))

    @whitelist.command(name="add", description="Add a Minecraft player to the whitelist.")
    async def whitelist_add(interaction: discord.Interaction, username: str) -> None:
        """After authorization, defer publicly and call server.add_to_whitelist(username) in a thread.

        Report added versus already whitelisted. MinecraftServer validates the name.
        """
        logger.info("/whitelist add requested: user=%s guild=%s channel=%s username=%r", interaction.user.id, interaction.guild_id, interaction.channel_id, username)
        await interaction.response.defer(ephemeral=False)
        changed = await asyncio.to_thread(server.add_to_whitelist, username)
        logger.info("/whitelist add result: user=%s username=%r changed=%s", interaction.user.id, username, changed)
        message = f"Added `{username}` to the whitelist." if changed else f"`{username}` is already whitelisted."
        await interaction.followup.send(
            embed=discord.Embed(title="Whitelist Add", description=message), ephemeral=False
        )
        logger.info("/whitelist add replies sent: user=%s", interaction.user.id)

    @whitelist.command(name="remove", description="Remove a Minecraft player from the whitelist.")
    async def whitelist_remove(interaction: discord.Interaction, username: str) -> None:
        """After authorization, defer publicly and call server.remove_from_whitelist(username) in a thread.

        Report removed versus not whitelisted. MinecraftServer validates the name.
        """
        logger.info("/whitelist remove requested: user=%s guild=%s channel=%s username=%r", interaction.user.id, interaction.guild_id, interaction.channel_id, username)
        await interaction.response.defer(ephemeral=False)
        changed = await asyncio.to_thread(server.remove_from_whitelist, username)
        logger.info("/whitelist remove result: user=%s username=%r changed=%s", interaction.user.id, username, changed)
        message = f"Removed `{username}` from the whitelist." if changed else f"`{username}` is not whitelisted."
        await interaction.followup.send(
            embed=discord.Embed(title="Whitelist Remove", description=message), ephemeral=False
        )
        logger.info("/whitelist remove replies sent: user=%s", interaction.user.id)

    tree.add_command(whitelist)

    @tree.command(name="help", description="Show the available bot commands.")
    @app_commands.guild_only()
    async def help_command(interaction: discord.Interaction) -> None:
        """Reply privately with command descriptions without contacting Minecraft."""
        logger.info("/help requested: user=%s guild=%s channel=%s", interaction.user.id, interaction.guild_id, interaction.channel_id)
        embed = discord.Embed(
            title="Bot Help",
            description=(
                "`/online` - Show players currently online in Minecraft.\n"
                "`/whitelist list` - Show whitelisted Minecraft players.\n"
                "`/whitelist add username` - Add a player to the whitelist.\n"
                "`/whitelist remove username` - Remove a player from the whitelist.\n"
                "`/help` - Show this help."
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info("/help completed: user=%s", interaction.user.id)

    @tree.error
    async def on_command_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Match command visibility, using a follow-up if already deferred/responded."""
        cause = getattr(error, "original", error)
        logger.warning("Command failed: command=%s user=%s guild=%s error=%r", interaction.command.qualified_name if interaction.command else "unknown", interaction.user.id, interaction.guild_id, cause)
        if isinstance(cause, ValueError):
            message = str(cause) or "Minecraft returned an empty response."
        elif isinstance(cause, (OSError, MCRconException)):
            message = "Minecraft RCON failed. The operation may not have completed; check before retrying."
        elif isinstance(cause, app_commands.CheckFailure):
            message = "You do not have permission to use this command."
        else:
            logger.error(
                "Discord command failed", exc_info=(type(cause), cause, cause.__traceback__)
            )
            message = "The command failed. Check the bot logs."
        embed = discord.Embed(title="Command Error", description=message[:4096], color=discord.Color.red())
        ephemeral = not (
            interaction.command and interaction.command.qualified_name in ("whitelist add", "whitelist remove")
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        logger.info("Error reply sent: user=%s", interaction.user.id)

    logger.info("Registered commands: %s", ", ".join(command.qualified_name for command in tree.walk_commands()))


async def _send_player_list(
    interaction: discord.Interaction, title: str, players: list[str], empty_message: str
) -> None:
    """Send private embeds, splitting descriptions at player boundaries."""
    pages = [""]
    for player in players:
        name = discord.utils.escape_markdown(player)
        if len(pages[-1]) + len(name) + 1 > 4096:
            pages.append("")
        pages[-1] += ("\n" if pages[-1] else "") + name
    for description in pages:
        embed = discord.Embed(
            title=f"{title} - {len(players)}", description=description or empty_message
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    logger.debug("Sent %d player-list embeds: user=%s players=%d", len(pages), interaction.user.id, len(players))

