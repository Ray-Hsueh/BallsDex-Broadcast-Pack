import logging
import io
from typing import Optional, cast

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import TextDisplay, LayoutView, Container, Section, Button, ActionRow

from ballsdex.core.utils import checks
from ballsdex.core.utils.menus import (
    Menu,
    ListSource,
    ItemFormatter,
    dynamic_chunks,
    iter_to_async,
)
from bd_models.models import GuildConfig, BallInstance
from settings.models import settings

log = logging.getLogger("ballsdex.packages.broadcast")



class Broadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Runs when cog loads"""
        guilds = [
            discord.Object(guild_id)
            async for guild_id in GuildConfig.objects.filter(admin_command_synced=True).values_list(
                "guild_id", flat=True
            )
        ]
        self.bot.tree.add_command(self.broadcast.app_command, guilds=guilds)

    async def get_broadcast_channels(self):
        channels = set()
        async for config in GuildConfig.objects.filter(enabled=True, spawn_channel__isnull=False):
            if config.spawn_channel:
                channels.add(config.spawn_channel)
        return channels

    @commands.hybrid_group()
    @app_commands.guilds(0)
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @checks.is_staff()
    async def broadcast(self, ctx: commands.Context):
        """
        Broadcast commands.
        """
        await ctx.send_help(ctx.command)


    @broadcast.command(name="channels", description="List all ball spawn channels")
    async def list_channels(self, ctx: commands.Context):
        await ctx.defer()
        channels = await self.get_broadcast_channels()
        if not channels:
            await ctx.send("No ball spawn channels are currently configured.")
            return

        entries: list[TextDisplay] = []
        
        for channel_id in channels:
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                guild = channel.guild
                if not guild:
                    continue
                
                text = f"## {guild.name}\n"
                text += f"- Channel: {channel.mention} (`{channel.id}`)\n"
                text += f"- Guild ID: `{guild.id}`\n"
                text += f"- Members: {guild.member_count:,}\n"

                total_catches = await BallInstance.objects.filter(server_id=guild.id).acount()
                if total_catches >= 20:
                    recent_catches = [
                        x async for x in BallInstance.objects.filter(
                            server_id=guild.id
                        ).order_by("-catch_date")[:10].select_related("player")
                    ]

                    if recent_catches:
                        unique_catchers = len(set(ball.player.discord_id for ball in recent_catches))
                        if unique_catchers == 1:
                            player = recent_catches[0].player
                            text += f"- \N{WARNING SIGN} **Last 10 balls caught by {player}**\n"

                entries.append(TextDisplay(text))

            except Exception:
                log.exception(f"Error processing channel {channel_id}")

        if not entries:
            await ctx.send("Could not retrieve any channel information.")
            return

        view = LayoutView()
        container = Container()
        view.add_item(container)
        
        pages = Menu(
            self.bot, 
            view, 
            ListSource(await dynamic_chunks(view, iter_to_async(entries))), 
            ItemFormatter(container, 1)
        )
        await pages.init()
        await ctx.send(view=view)

    @broadcast.command(name="server", description="Send a broadcast message to all ball spawn channels")
    @app_commands.describe(
        mode="Broadcast mode",
        message="The text message to send",
        attachment="An optional image attachment",
        anonymous="Whether to hide the sender's name"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Text and Image", value="both"),
        app_commands.Choice(name="Text Only", value="text"),
        app_commands.Choice(name="Image Only", value="image")
    ])
    async def broadcast_server(
        self, 
        ctx: commands.Context, 
        mode: str,
        message: Optional[str] = None,
        attachment: Optional[discord.Attachment] = None,
        anonymous: bool = False
    ):
        await ctx.defer()
        
        if mode == "text" and not message:
            await ctx.send("You must provide a message when selecting 'Text Only' mode.")
            return
        if mode == "image" and not attachment:
            await ctx.send("You must provide an image when selecting 'Image Only' mode.")
            return
        if mode == "both" and not message and not attachment:
            await ctx.send("You must provide a message or image when selecting 'Text and Image' mode.")
            return

        channels = await self.get_broadcast_channels()
        if not channels:
            await ctx.send("No ball spawn channels are currently configured.")
            return

        await ctx.send("Broadcasting message...")
        
        success_count = 0
        fail_count = 0
        failed_channels = []
        
        broadcast_message = None
        if message:
            broadcast_message = (
                "🔔 **System Announcement** 🔔\n"
                "------------------------\n"
                f"{message}\n"
                "------------------------\n"
            )
            if not anonymous:
                broadcast_message += f"*Sent by {ctx.author.name}*"
        
        file_data = None
        filename = None
        is_spoiler = False
        
        if attachment and mode in ["both", "image"]:
            try:
                file_data = await attachment.read()
                filename = attachment.filename
                is_spoiler = attachment.is_spoiler()
            except Exception:
                log.exception("Error downloading attachment")
                await ctx.send("An error occurred while downloading the attachment. Only the text message will be sent.")
        
        for channel_id in channels:
            try:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    file_to_send = None
                    if file_data:
                        file_to_send = discord.File(
                            io.BytesIO(file_data),
                            filename=filename,
                            spoiler=is_spoiler
                        )

                    if mode == "text":
                        await channel.send(broadcast_message)
                    elif mode == "image" and file_to_send:
                        await channel.send(file=file_to_send)
                    else:  # both
                        if file_to_send and broadcast_message:
                            await channel.send(broadcast_message, file=file_to_send)
                        elif file_to_send:
                            await channel.send(file=file_to_send)
                        elif broadcast_message:
                            await channel.send(broadcast_message)
                    success_count += 1
                else:
                    fail_count += 1
                    failed_channels.append(f"Unknown Channel (ID: {channel_id})")
            except Exception:
                log.exception(f"Error broadcasting to channel {channel_id}")
                fail_count += 1
                if channel:
                    failed_channels.append(f"{channel.guild.name} - #{channel.name}")
                else:
                    failed_channels.append(f"Unknown Channel (ID: {channel_id})")
        
        result_message = f"Broadcast complete!\nSuccessfully sent: {success_count} channels\nFailed: {fail_count} channels"
        if failed_channels:
            # Truncate if too long
            failed_text = "\n".join(failed_channels)
            if len(failed_text) > 1000:
                failed_text = failed_text[:1000] + "... (truncated)"
            result_message += "\n\nFailed channels:\n" + failed_text
        
        await ctx.send(result_message)

    @broadcast.command(name="dm", description="Send a DM broadcast to specific users")
    @app_commands.describe(
        message="The message you are going to send",
        user_ids="A comma-separated list of user IDs",
        anonymous="Whether to hide the sender's name"
    )
    async def broadcast_dm(
        self, 
        ctx: commands.Context, 
        message: str,
        user_ids: str,
        anonymous: bool = False
    ):
        await ctx.defer()
        user_id_list = [uid.strip() for uid in user_ids.split(",")]
        if not user_id_list:
            await ctx.send("Please provide at least one user ID.")
            return

        await ctx.send("Starting DM broadcast...")
        
        success_count = 0
        fail_count = 0
        failed_users = []
        
        dm_message = (
            "🔔 **System DM** 🔔\n"
            "------------------------\n"
            f"{message}\n"
            "------------------------\n"
        )
        if not anonymous:
            dm_message += f"*Sent by {ctx.author.name}*"
        
        for user_id in user_id_list:
            try:
                user = await self.bot.fetch_user(int(user_id))
                if user:
                    await user.send(dm_message)
                    success_count += 1
                else:
                    fail_count += 1
                    failed_users.append(f"Unknown User (ID: {user_id})")
            except discord.Forbidden:
                fail_count += 1
                failed_users.append(f"User ID: {user_id} (DMs Closed)")
            except Exception:
                log.exception(f"Error sending DM to user {user_id}")
                fail_count += 1
                failed_users.append(f"User ID: {user_id}")
        
        result_message = f"DM broadcast complete!\nSuccessfully sent: {success_count} users\nFailed: {fail_count} users"
        if failed_users:
            failed_text = "\n".join(failed_users)
            if len(failed_text) > 1000:
                failed_text = failed_text[:1000] + "... (truncated)"
            result_message += "\n\nFailed users:\n" + failed_text
        
        await ctx.send(result_message)
