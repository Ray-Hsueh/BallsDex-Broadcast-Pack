async def setup(bot):
    from .cog import Broadcast
    await bot.add_cog(Broadcast(bot))