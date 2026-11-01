"""Minecraft server commands over RCON."""

import logging
import os
import re

from dotenv import load_dotenv
from mcrcon import MCRcon

logger = logging.getLogger(__name__)


class MinecraftResponseError(ValueError):
    """A failed or unexpected Minecraft response, preserved as the error message."""


class MinecraftServer:
    """Store RCON settings and open a fresh connection for each command."""

    def __init__(self) -> None:
        load_dotenv()
        self.host = os.getenv("RCON_HOST", "127.0.0.1")
        self.password = os.getenv("RCON_PASSWORD", "")
        if not self.host.strip():
            logger.error("RCON_HOST is empty")
            raise ValueError("RCON_HOST must not be empty.")
        if not self.password:
            logger.error("RCON_PASSWORD is missing")
            raise ValueError("Set RCON_PASSWORD in .env before running Minecraft commands.")

        try:
            self.port = int(os.getenv("RCON_PORT", "25575"))
        except ValueError:
            logger.error("RCON_PORT is not an integer")
            raise ValueError("RCON_PORT must be an integer from 1 to 65535.") from None
        if not 1 <= self.port <= 65535:
            logger.error("RCON_PORT is out of range")
            raise ValueError("RCON_PORT must be an integer from 1 to 65535.")
        logger.info("RCON settings loaded: host=%r port=%d", self.host, self.port)

    def _command(self, command: str) -> str:
        logger.info("RCON command starting: host=%r port=%d command=%r", self.host, self.port, command)
        try:
            with MCRcon(self.host, self.password, port=self.port, timeout=5) as mc:
                logger.debug("RCON connected and authenticated")
                response = mc.command(command)
                logger.debug("RCON response: %r", response)
            logger.info("RCON command completed and connection closed: command=%r", command)
            return response
        except Exception as error:
            logger.warning("RCON command failed: command=%r error_type=%s", command, type(error).__name__)
            raise

    def _whitelist(self, action: str, username: str) -> bool:
        if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_]{3,16}", username):
            logger.warning("Rejected invalid Minecraft username: %r", username)
            raise ValueError("Username must be 3-16 ASCII letters, digits, or underscores.")
        response = self._command(f"whitelist {action} {username}").strip()
        success, unchanged = {
            "add": (f"Added {username} to the whitelist", "Player is already whitelisted"),
            "remove": (f"Removed {username} from the whitelist", "Player is not whitelisted"),
        }[action]
        # Minecraft may return the account's canonical capitalization.
        if response.lower() == success.lower():
            logger.info("Whitelist %s changed: username=%r", action, username)
            return True
        if response == unchanged:
            logger.info("Whitelist %s unchanged: username=%r", action, username)
            return False
        logger.warning("Unexpected whitelist %s response: %r", action, response)
        raise MinecraftResponseError(response)

    def add_to_whitelist(self, username: str) -> bool:
        """Add a Java player; return False if already whitelisted."""
        return self._whitelist("add", username)

    def remove_from_whitelist(self, username: str) -> bool:
        """Remove a Java player; return False if not whitelisted."""
        return self._whitelist("remove", username)

    @staticmethod
    def _parse_player_list(response: str, pattern: str) -> list[str]:
        match = re.fullmatch(pattern, response.strip())
        if not match:
            logger.warning("Unexpected player-list response: %r", response)
            raise MinecraftResponseError(response)
        names = match[2].split(", ") if match[2] else []
        if len(names) != int(match[1]) or any(
            not re.fullmatch(r"[A-Za-z0-9_]{1,16}", name) for name in names
        ):
            logger.warning("Invalid names or count in player-list response: %r", response)
            raise MinecraftResponseError(response)
        logger.info("Parsed player list: players=%d", len(names))
        return names

    def list_online_players(self) -> list[str]:
        """Return online player names from Paper's default English response."""
        return self._parse_player_list(
            self._command("list"),
            r"There are ([0-9]+) of a max of [0-9]+ players online: ?(.*)",
        )

    def list_whitelist(self) -> list[str]:
        """Return whitelisted player names from Paper's default English response."""
        response = self._command("whitelist list")
        if response.strip() == "There are no whitelisted players":
            logger.info("Whitelist is empty")
            return []
        return self._parse_player_list(
            response, r"There are ([0-9]+) whitelisted player\(s\): ?(.*)"
        )
