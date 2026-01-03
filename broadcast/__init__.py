import logging
import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.broadcast")

LOGO = textwrap.dedent(r"""
    +----------------------------------------+
    |  Ballsdex Broadcast Pack by Ray Hsueh  |
    |       Licensed under Apache 2.0        |
    +----------------------------------------+
""").strip()


async def setup(bot: "BallsDexBot"):
    print(LOGO)
    log.info("Loading Broadcast package...")
    from .cog import Broadcast
    await bot.add_cog(Broadcast(bot))
    log.info("Broadcast package loaded successfully!")