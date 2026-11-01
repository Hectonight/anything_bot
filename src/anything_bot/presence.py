"""Live Discord player count over a dedicated persistent RCON connection."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress

import discord
from discord.ext import tasks
from mcrcon import MCRconException

from anything_bot.mc_cmds import MinecraftResponseError, MinecraftServer, _ThreadedRcon

logger = logging.getLogger(__name__)


class PresenceMonitor:
    def __init__(
        self, client: discord.Client, host: str, port: int, password: str,
        *, server_name: str = "Anything Server",
    ) -> None:
        self.client = client
        self.server_name = server_name
        self._settings = (host, port, password)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="presence-rcon")
        self._connection: _ThreadedRcon | None = None
        self._last_presence: tuple[str, discord.Status] | None = None
        self._closed = False

    def start(self) -> None:
        """Start polling once; construction and startup do not open RCON sockets."""
        if not self._closed and not self._update.is_running():
            self._update.start()
            logger.info("Presence monitor started: refresh=10s")

    def invalidate(self) -> None:
        """Reapply the activity on the next refresh after a Discord reconnect."""
        self._last_presence = None

    def _disconnect(self) -> None:
        """Close the socket on its worker, after any earlier operation finishes."""
        if self._connection is not None:
            try:
                self._connection.disconnect()
            finally:
                self._connection = None
                logger.info("Presence RCON connection closed")

    def _poll(self) -> int:
        """Run exclusively on the dedicated worker; reuse the socket between polls."""
        try:
            if self._connection is None:
                host, port, password = self._settings
                self._connection = _ThreadedRcon(host, password, port=port, timeout=5)
                self._connection.connect()
                logger.info("Presence RCON connected: host=%r port=%d", host, port)
            response = self._connection.command("list")
            players = MinecraftServer._parse_player_list(
                response, r"There are ([0-9]+) of a max of [0-9]+ players online: ?(.*)"
            )
            return len(players)
        except MinecraftResponseError:
            raise
        except Exception:
            self._disconnect()
            raise

    async def _set_presence(self, text: str, status: discord.Status) -> None:
        if self._last_presence != (text, status):
            await self.client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.playing, name=self.server_name, state=text
                ),
                status=status,
            )
            self._last_presence = (text, status)
            logger.debug("Presence updated: %s", text)

    @tasks.loop(seconds=10)
    async def _update(self) -> None:
        await self.client.wait_until_ready()
        try:
            count = await asyncio.get_running_loop().run_in_executor(self._executor, self._poll)
            text = f"{count} {'player' if count == 1 else 'players'} online"
            status = discord.Status.online
            logger.debug("Presence poll completed: players=%d", count)
        except (OSError, MCRconException, MinecraftResponseError) as error:
            logger.warning("Presence poll failed: %r", error)
            text, status = "Player count unavailable", discord.Status.idle
        except Exception:
            logger.exception("Unexpected presence polling failure")
            text, status = "Player count unavailable", discord.Status.idle
        try:
            await self._set_presence(text, status)
        except Exception:
            logger.exception("Discord presence update failed; will retry next refresh")

    @_update.before_loop
    async def _before_update(self) -> None:
        await self.client.wait_until_ready()
        try:
            await self._set_presence("Checking player count…", discord.Status.idle)
        except Exception:
            logger.exception("Initial Discord presence update failed")

    async def close(self) -> None:
        """Stop polling, finish in-flight work, then close the socket and worker."""
        if self._closed:
            return
        self._closed = True
        self._update.cancel()
        task = self._update.get_task()
        try:
            if task is not None:
                with suppress(asyncio.CancelledError):
                    await task
        finally:
            try:
                await asyncio.get_running_loop().run_in_executor(self._executor, self._disconnect)
            finally:
                self._executor.shutdown(wait=True)
                logger.info("Presence monitor stopped")
