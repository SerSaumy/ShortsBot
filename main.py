# -----------------------------------------------------------------------------
# ShortsBot Main Application Loader - FINAL RELOAD FIX
# -----------------------------------------------------------------------------
import asyncio
import logging
import discord
from discord.ext import commands

class ShortsBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            import yaml; self.config = yaml.safe_load(open("config.yaml", "r", encoding='utf-8'))
        except Exception: self.config = None
    async def close(self):
        logging.info("Shutdown sequence initiated...")
        if self.config:
            channel = self.get_channel(int(self.config['bot'].get('channel_id')))
            if channel:
                try: await channel.send("🛑 **ShortsBot is shutting down.**")
                except Exception: pass
        if self.http: await self.http.close()
        await super().close()

async def main():
    try:
        import yaml; config = yaml.safe_load(open("config.yaml", "r", encoding='utf-8'))
    except Exception as e: print(f"CRITICAL: Could not load config.yaml. Error: {e}"); return
    
    intents = discord.Intents.default(); intents.messages = True; intents.message_content = True
    bot = ShortsBot(command_prefix="!", intents=intents, owner_id=int(config['bot']['owner_id']))

    @bot.command(name="reload")
    @commands.is_owner()
    async def reload_cog(ctx):
        """Reloads all bot modules and re-initializes the cog."""
        await ctx.send("🔄 **Reloading...** Please wait.")
        logging.info("🔄 Owner requested a full reload...")
        try:
            import importlib, sys, utils, helpers, workflows
            # Reload helper modules first
            if 'utils' in sys.modules: importlib.reload(utils)
            if 'helpers' in sys.modules: importlib.reload(helpers)
            if 'workflows' in sys.modules: importlib.reload(workflows)
            
            # Reload the main cog extension
            await bot.reload_extension("bot_cog")
            
            # After reloading, get the new cog instance and explicitly set it up
            reloaded_cog = bot.get_cog("BotCog")
            if reloaded_cog:
                await reloaded_cog.setup_cog() # Call our setup function
                await ctx.send("✅ **Reload and setup complete!** Bot is ready.")
                ctx.command.reset_cooldown(ctx)  # Reset cooldown if any
                await ctx.invoke(bot.get_command("start"))  # <-- This line ensures proper invocation
            else:
                await ctx.send("❌ **CRITICAL ERROR:** Cog failed to load after reload.")

        except Exception as e:
            await ctx.send(f"❌ **Reload failed:**\n```\n{e}\n```")

    async with bot:
        await bot.load_extension("bot_cog")
        await bot.start(config['bot']['discord_token'])

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logging.info("Shutdown signal received via Ctrl+C.")
    finally: logging.info("🛑 Bot has been shut down cleanly.")