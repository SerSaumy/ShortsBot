# -----------------------------------------------------------------------------
# ShortsBot Main Logic Cog - V3.0 AUTONOMOUS
# -----------------------------------------------------------------------------
import asyncio, logging, time
from pathlib import Path
from datetime import datetime, timezone
import os
import discord
from discord.ext import commands, tasks
import utils, subtitles, helpers
from workflows import WorkflowManager

async def is_in_correct_channel(ctx):
    cog = ctx.bot.get_cog('BotCog');
    if not cog or not cog.cog_is_ready: await ctx.send("⌛ Bot is still initializing...", delete_after=5); return False
    return ctx.channel.id == int(cog.config['bot']['channel_id'])

class BotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot; self.is_manual_processing_running = False; self.is_waiting_for_user_response = False
        self.cog_is_ready = False; self.youtube = None; self.config = None; self.progress = None
        self.session_ignore_list = set(); self.workflows = None
    def is_ready(self): return self.cog_is_ready
    def cog_unload(self):
        if self.main_processing_loop.is_running(): self.main_processing_loop.cancel()
        self.cog_is_ready = False
    
    @commands.Cog.listener()
    async def on_ready(self):
        if self.cog_is_ready: return
        await self.setup_cog()

    async def setup_cog(self):
        self.cog_is_ready = False; utils.setup_folders(); utils.setup_logger(); logging.info("⚙️ Performing cog setup...")
        self.config = utils.load_config()
        if not self.config: logging.critical("Config could not be loaded."); return
        self.workflows = WorkflowManager(self.bot, self)
        channel = self.bot.get_channel(int(self.config['bot']['channel_id']))
        is_online_mode = self.config['youtube'].get('youtube_online_mode', True)
        startup_message = await channel.send(f"🤖 **Initializing ({'Online' if is_online_mode else 'Offline'})...**") if channel else None
        if self.config.get('subtitles', {}).get('enabled'):
            if 'imagemagick_path' in self.config['subtitles']: subtitles.configure_moviepy(self.config['subtitles']['imagemagick_path'])
            subtitles.load_whisper_model(self.config['subtitles']['whisper_model'])
        if is_online_mode:
            self.progress = utils.load_progress(); self.youtube = await asyncio.to_thread(helpers.get_youtube_service, self.config)
            if self.youtube:
                if startup_message: await startup_message.edit(content="✅ **ShortsBot is ONLINE and ready!**")
                await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for work..."))
            else:
                if startup_message: await startup_message.edit(content="❌ **CRITICAL ERROR:** Could not connect to YouTube.")
        else:
            self.progress = {"source_videos": {}, "last_scheduled_time": None, "quota_tracker": {}}
            self.youtube = None;
            if startup_message: await startup_message.edit(content="✅ **ShortsBot is in OFFLINE mode.**")
            await self.bot.change_presence(activity=discord.Game(name="in Offline Mode"))
        if not self.main_processing_loop.is_running(): self.main_processing_loop.start()
        self.cog_is_ready = True; logging.info("✅ Cog setup complete.")
        
    @commands.command(name="start")
    @commands.check(is_in_correct_channel)
    async def start_processing(self, ctx):
        if self.is_manual_processing_running or self.is_waiting_for_user_response: await ctx.send("⚠️ Bot is already busy processing. Please wait."); return
        self.is_manual_processing_running = True; self.session_ignore_list.clear()
        self.main_processing_loop.restart()
        await ctx.send("✅ **Manual Start:** Checking for new videos to process...")
    
    @tasks.loop(minutes=5)
    async def main_processing_loop(self):
        if self.is_waiting_for_user_response: return
        self.is_waiting_for_user_response = True
        try:
            await self.workflows.run_autonomous_workflow(process_new=self.is_manual_processing_running)
        except Exception as e: logging.error(f"💥 Main loop error: {e}", exc_info=True)
        finally:
            self.is_waiting_for_user_response = False
            self.is_manual_processing_running = False

    @main_processing_loop.before_loop
    async def before_main_loop(self): await self.bot.wait_until_ready()

    # ... (the rest of the commands) ...
    @commands.command(name="status")
    @commands.check(is_in_correct_channel)
    async def status(self, ctx):
        online_status = "🟢 ONLINE" if self.config['youtube'].get('youtube_online_mode') else "⚪ OFFLINE"; processing_status = "▶️ ACTIVE" if self.is_manual_processing_running or self.is_waiting_for_user_response else "⏹️ IDLE"
        status_message = f"**Mode:** `{online_status}` | **Status:** `{processing_status}`"
        await ctx.send(f"**ShortsBot Status:**\n{status_message}")
    @commands.command(name="stop")
    @commands.check(is_in_correct_channel)
    async def stop_processing(self, ctx):
        if not (self.is_manual_processing_running or self.is_waiting_for_user_response): await ctx.send("⚠️ Bot is already idle.")
        else:
            self.is_manual_processing_running = False
            await ctx.send("✅ **Processing stopped!** Bot will finish its current action and return to idle.")
    @commands.command(name="end")
    @commands.check(is_in_correct_channel)
    async def end_bot(self, ctx): await self.bot.close()
    @commands.command(name="quota")
    @commands.check(is_in_correct_channel)
    async def quota(self, ctx):
        if not self.config['youtube'].get('youtube_online_mode'): await ctx.send("⚪ Bot is in offline mode."); return
        total_limit = self.config['youtube']['daily_quota_limit']; today_utc_str = datetime.now(timezone.utc).strftime('%Y-%m-%d'); quota_data = self.progress.get('quota_tracker', {}); spent_today = 0
        if quota_data.get('date') == today_utc_str: spent_today = quota_data.get('spent', 0)
        remaining = total_limit - spent_today; embed = discord.Embed(title="📊 YouTube API Quota Status", color=discord.Color.blue()); embed.add_field(name="Daily Limit", value=f"`{total_limit:,}` units", inline=False); embed.add_field(name="Spent Today (Estimated)", value=f"`{spent_today:,}` units", inline=False); embed.add_field(name="Remaining (Estimated)", value=f"`{remaining:,}` units", inline=False)
        embed.set_footer(text="This is an estimate. Quota resets daily at midnight PST."); await ctx.send(embed=embed)
    @commands.command(name="schedule")
    @commands.check(is_in_correct_channel)
    async def schedule(self, ctx):
        if not self.config['youtube'].get('youtube_online_mode'): await ctx.send("⚪ Bot is in offline mode."); return
        scheduled_videos = []; now_utc = datetime.now(timezone.utc)
        for source_video, data in self.progress.get('source_videos', {}).items():
            for clip_filename, clip_data in data.get('clips', {}).items():
                if clip_data.get('status') == 'uploaded' and 'publish_at' in clip_data:
                    publish_time = datetime.fromisoformat(clip_data['publish_at'].replace('Z', '+00:00'))
                    if publish_time > now_utc: scheduled_videos.append((publish_time, clip_filename, clip_data['youtube_id']))
        if not scheduled_videos: await ctx.send("🗓️ No videos currently scheduled."); return
        scheduled_videos.sort(key=lambda x: x[0]); embed = discord.Embed(title="🗓️ Upcoming Video Schedule", color=discord.Color.green()); description = ""
        for publish_time, clip_filename, video_id in scheduled_videos[:10]:
            display_time = publish_time.strftime('%b %d, %Y at %I:%M %p (UTC)'); base_title = Path(clip_filename).stem.replace('_', ' ').title(); video_url = f"https://www.youtube.com/watch?v={video_id}"; description += f"**[{base_title}]({video_url})**\n> {display_time}\n"
        embed.description = description; embed.set_footer(text=f"Showing {len(scheduled_videos)} upcoming videos."); await ctx.send(embed=embed)
    @commands.command(name="preview")
    @commands.check(is_in_correct_channel)
    async def preview(self, ctx, *, video_name: str = None):
        if video_name is None: await ctx.send("⚠️ **Usage:** `!preview \"My Video File.mp4\"`"); return
        video_path = os.path.join(utils.INPUT_VIDEOS_DIR, video_name)
        if not os.path.exists(video_path): await ctx.send(f"❌ Could not find `{video_name}`."); return
        await ctx.send(f"🔬 Analyzing `{video_name}`..."); total_clips = await self.workflows.get_total_clips(video_name)
        if total_clips is None: return
        clip_duration = self.config['video']['clip_duration_seconds']; overlap = self.config['video']['clip_overlap_seconds']
        embed = discord.Embed(title=f"🎞️ Clipping Preview for `{video_name}`", description=f"Can be split into **{total_clips}** clips.", color=discord.Color.purple()); preview_text = ""
        for i in range(total_clips):
            start_seconds = i * (clip_duration - overlap); end_seconds = start_seconds + clip_duration; start_time_str = time.strftime('%M:%S', time.gmtime(start_seconds)); end_time_str = time.strftime('%M:%S', time.gmtime(end_seconds))
            preview_text += f"**Part {i+1}:** `{start_time_str}` - `{end_time_str}`\n"
            if i >= 14: preview_text += f"\n...and {total_clips - 15} more."; break
        embed.add_field(name="Clip Timestamps", value=preview_text, inline=False); await ctx.send(embed=embed)
    async def _log_quota_usage(self, action: str):
        if not self.config['youtube'].get('youtube_online_mode'): return
        cost = self.config['youtube']['api_costs'].get(action, 0);
        if cost == 0: return
        today_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if 'quota_tracker' not in self.progress or self.progress['quota_tracker'].get('date') != today_utc:
            self.progress['quota_tracker'] = {'date': today_utc, 'spent': 0, 'uploads_today': 0}
        self.progress['quota_tracker']['spent'] += cost
        if action == 'upload': self.progress['quota_tracker']['uploads_today'] = self.progress['quota_tracker'].get('uploads_today', 0) + 1
        total_spent = self.progress['quota_tracker']['spent']; total_limit = self.config['youtube']['daily_quota_limit']; remaining = total_limit - total_spent
        channel = self.bot.get_channel(int(self.config['bot']['channel_id']))
        if channel: await channel.send(f"📊 Quota Update: `{action}` cost **{cost}**. Est. usage: **{total_spent:,} / {total_limit:,}** (`{remaining:,}` remaining).")
        utils.save_progress(self.progress)
async def setup(bot): await bot.add_cog(BotCog(bot))