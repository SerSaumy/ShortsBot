# -----------------------------------------------------------------------------
# ShortsBot Core Workflow Logic - STABLE VERSION
# -----------------------------------------------------------------------------
import asyncio, logging, os, shutil
from pathlib import Path
from datetime import datetime, timezone

import discord
import utils, helpers, subtitles

class WorkflowManager:
    def __init__(self, bot, cog):
        self.bot = bot; self.cog = cog
        self.is_online = self.cog.config['youtube'].get('youtube_online_mode', True)

    async def run_autonomous_workflow(self, process_new: bool):
        channel = self.bot.get_channel(int(self.cog.config['bot']['channel_id']))
        pending_clips = self._get_pending_clips()
        if pending_clips: await self.process_pending_uploads(pending_clips); return
        failed_clips = [f for f in os.listdir(utils.FAILED_UPLOADS_DIR) if f.endswith(('.mp4', '.mkv'))]
        if failed_clips: await self.process_failed_uploads(failed_clips); return
        if process_new:
            work_item, work_type = self.find_new_work()
            if not work_item: await channel.send("✅ No new videos to process."); return
            if work_type == "processing": await self.resume_in_progress_video(work_item)
            elif work_type == "new": await self.process_new_video(work_item)
            elif work_type == "completed": await self.handle_completed_video(work_item)

    async def upload_clip_task(self, channel, source_video_name, clip_path, clip_number, is_retry=False):
        if not self.is_online: return
        clip_filename = os.path.basename(clip_path)
        next_schedule_timestamp = helpers.get_next_schedule_time(self.cog.progress.get('last_scheduled_time'))
        if next_schedule_timestamp is None: await channel.send("❌ Scheduling Error: Could not get next slot."); return
        if not is_retry: self.cog.progress['last_scheduled_time'] = next_schedule_timestamp
        
        base_title = Path(source_video_name).stem.replace('_', ' ').replace('.', ' ').title()
        title = f"{base_title} - Part {clip_number} #shorts"
        
        playlist_id = self.cog.progress['source_videos'][source_video_name]['playlist_id']
        playlist_link = f"https://www.youtube.com/playlist?list={playlist_id}"
        hashtags = ' '.join(self.cog.config['default_hashtags'])
        
        description = self.cog.config['description_template'].format(
            title=base_title,
            playlist_link=playlist_link,
            hashtags=hashtags
        )

        video_id, error_message = await helpers.upload_video(self.cog.youtube, self.cog.config, clip_path, title, description, self.cog.config['youtube']['default_category_id'], self.cog.config['default_hashtags'], next_schedule_timestamp)
        
        if video_id:
            await self.cog._log_quota_usage('upload')
            success = await helpers.add_video_to_playlist(self.cog.youtube, playlist_id, video_id)
            if success: await self.cog._log_quota_usage('playlist_item_insert')
            
            scheduled_time_obj = datetime.fromtimestamp(next_schedule_timestamp, tz=timezone.utc)
            self.cog.progress['source_videos'][source_video_name]['clips'][clip_filename] = {
                'status': 'uploaded', 'youtube_id': video_id, 
                'publish_at': scheduled_time_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            formatted_time = scheduled_time_obj.strftime('%b %d, %Y at %I:%M %p (UTC)')
            await channel.send(f"✅ **Upload Complete:** `{title}`\n> Scheduled for **{formatted_time}**")
            os.remove(clip_path)
        else:
            self.cog.progress['source_videos'][source_video_name]['clips'][clip_filename] = {'status': 'upload_failed', 'reason': error_message}
            await channel.send(f"❌ **Upload FAILED:** `{title}`\n> **Reason:** `{error_message}`")
            if not is_retry: shutil.move(clip_path, os.path.join(utils.FAILED_UPLOADS_DIR, clip_filename))
        
        utils.save_progress(self.cog.progress)
        
    # ... (The rest of the file is correct and can remain unchanged)
    def find_new_work(self):
        all_videos_in_folder = {f for f in os.listdir(utils.INPUT_VIDEOS_DIR) if f.endswith(('.mp4', '.mkv'))}
        if not all_videos_in_folder: return None, None
        in_progress_videos = [v for v in all_videos_in_folder if self.cog.progress['source_videos'].get(v, {}).get('status') == 'processing']
        if in_progress_videos: return in_progress_videos[0], "processing"
        new_videos = [v for v in all_videos_in_folder if v not in self.cog.progress['source_videos']]
        if new_videos: return new_videos[0], "new"
        if self.is_online:
            completed_video = next((v for v in all_videos_in_folder if self.cog.progress['source_videos'].get(v, {}).get('status') == 'completed' and v not in self.cog.session_ignore_list), None)
            if completed_video: return completed_video, "completed"
        return None, None
    def _get_pending_clips(self):
        pending = []
        for source_name, source_data in self.cog.progress.get('source_videos', {}).items():
            for clip_name, clip_data in source_data.get('clips', {}).items():
                if clip_data.get('status') == 'pending_upload':
                    clip_path = os.path.join(utils.PROCESSED_CLIPS_DIR, clip_name)
                    if os.path.exists(clip_path):
                        pending.append({'source': source_name, 'clip_name': clip_name, 'path': clip_path})
        return pending
    def _parse_clip_number(self, clip_filename: str) -> int | None:
        try:
            stem = Path(clip_filename).stem; part_str = stem.split(' part ')[-1]; num_str = part_str.split('_')[0]; return int(num_str)
        except (IndexError, ValueError): logging.error(f"Could not parse clip number from: {clip_filename}"); return None
    async def process_pending_uploads(self, pending_clips):
        channel = self.bot.get_channel(int(self.cog.config['bot']['channel_id'])); await channel.send(f"📬 Found **{len(pending_clips)}** clips in the upload queue. Checking daily limit...")
        max_daily_uploads = self.cog.config['bot']['max_uploads_per_day']; today_utc_str = datetime.now(timezone.utc).strftime('%Y-%m-%d'); quota_data = self.cog.progress.get('quota_tracker', {})
        uploads_today = quota_data.get('uploads_today', 0) if quota_data.get('date') == today_utc_str else 0
        uploads_left_today = max_daily_uploads - uploads_today
        if uploads_left_today <= 0: await channel.send("🚫 Daily upload limit reached for today."); return
        await channel.send(f"   - Uploading up to **{uploads_left_today}** clips now...")
        clips_to_upload_now = pending_clips[:uploads_left_today]
        for item in clips_to_upload_now:
            clip_number = self._parse_clip_number(item['clip_name'])
            if clip_number is None: continue
            await self.upload_clip_task(channel, item['source'], item['path'], clip_number)
    async def process_failed_uploads(self, failed_clips):
        channel = self.bot.get_channel(int(self.cog.config['bot']['channel_id'])); await channel.send(f"♻️ Retrying **{len(failed_clips)}** failed uploads...")
        for clip_filename in failed_clips:
            clip_number = self._parse_clip_number(clip_filename)
            if clip_number is None: continue
            try:
                base_name = " ".join(Path(clip_filename).stem.split(' part ')[0:-1]); source_video_name = base_name + Path(clip_filename).suffix
                clip_path = os.path.join(utils.FAILED_UPLOADS_DIR, clip_filename)
                if source_video_name not in self.cog.progress['source_videos']: continue
                await self.upload_clip_task(channel, source_video_name, clip_path, clip_number, is_retry=True)
            except Exception as e: logging.error(f"Could not parse failed clip '{clip_filename}': {e}")
        await channel.send("✅ Re-upload process complete.")
    async def process_new_video(self, source_video_name): await self.run_full_process(source_video_name, start_clip_index=0)
    async def resume_in_progress_video(self, source_video_name):
        channel = self.bot.get_channel(int(self.cog.config['bot']['channel_id'])); video_data = self.cog.progress['source_videos'][source_video_name]
        total_possible = await self.get_total_clips(source_video_name);
        if total_possible is None: return
        clips_done_count = len(video_data.get('clips', {})); clips_remaining = total_possible - clips_done_count
        if clips_remaining <= 0: self.cog.progress['source_videos'][source_video_name]['status'] = 'completed'; utils.save_progress(self.cog.progress); return
        await channel.send(f"▶️ **Resuming `{source_video_name}`**.\n> `{clips_done_count}/{total_possible}` done. **{clips_remaining}** remaining.\nHow many **more**?")
        def check(m): return m.channel == channel and (m.content.lower() == 'all' or (m.content.isdigit() and 1 <= int(m.content) <= clips_remaining))
        try:
            msg = await self.bot.wait_for('message', timeout=300.0, check=check); num_to_process = clips_remaining if msg.content.lower() == 'all' else int(msg.content)
            await self.run_full_process(source_video_name, start_clip_index=clips_done_count, num_to_process=num_to_process)
        except asyncio.TimeoutError: await channel.send("⏰ Timed out.")
    async def handle_completed_video(self, source_video_name):
        channel = self.bot.get_channel(int(self.cog.config['bot']['channel_id'])); await channel.send(f"⚠️ **Notice:** `{source_video_name}` is fully processed.\n➡️ Reply `reprocess`, `ignore`, or `stop`.")
        def check(m): return m.channel == channel and m.content.lower() in ['reprocess', 'ignore', 'stop']
        try:
            msg = await self.bot.wait_for('message', timeout=300.0, check=check)
            if msg.content.lower() == 'reprocess': del self.cog.progress['source_videos'][source_video_name]; utils.save_progress(self.cog.progress); await channel.send(f"✅ Records deleted for `{source_video_name}`.")
            elif msg.content.lower() == 'ignore': self.cog.session_ignore_list.add(source_video_name); await channel.send(f"👍 Ignoring `{source_video_name}`.")
            elif msg.content.lower() == 'stop': self.cog.is_manual_processing_running = False; await channel.send("✅ Processing stopped.")
        except asyncio.TimeoutError: await channel.send("⏰ Timed out. Ignoring."); self.cog.session_ignore_list.add(source_video_name)
    async def create_clip(self, channel, source_video_path, clip_number):
        progress_message = await channel.send(f"⏳ Preparing clip #{clip_number}...")
        async def update_progress(p):
            bar = utils.create_progress_bar(p); print(f"\r-> Creating Clip #{clip_number}: {bar}", end="")
            try: await progress_message.edit(content=f"⚙️ Creating clip #{clip_number}: `{bar}`")
            except discord.NotFound: pass
        clip_duration = self.cog.config['video']['clip_duration_seconds']; overlap = self.cog.config['video']['clip_overlap_seconds']
        start_time = (clip_number - 1) * (clip_duration - overlap)
        base_clip_path = await utils.split_video_into_clip_with_progress(source_video_path, clip_number, start_time, clip_duration, progress_callback=update_progress)
        print();
        if not base_clip_path: await progress_message.edit(content=f"❌ **Error creating base clip #{clip_number}.**"); return None
        if self.cog.config['subtitles']['enabled']:
            subtitles.load_whisper_model(self.cog.config['subtitles']['whisper_model'])
            await progress_message.edit(content=f"🎤 Generating subtitles...")
            srt_path = await subtitles.generate_subtitles(base_clip_path)
            if srt_path:
                await progress_message.edit(content=f"🔥 Burning subtitles...")
                final_clip_path = await subtitles.burn_subtitles_into_video(base_clip_path, srt_path, self.cog.config['subtitles']['style'])
                os.remove(srt_path)
                if final_clip_path:
                    await progress_message.edit(content=f"✅ Subtitles added!")
                    os.remove(base_clip_path)
                    return final_clip_path
                else:
                    await progress_message.edit(content=f"❌ **Error burning subtitles.** Clip will be unsubtitled.")
                    return base_clip_path
            else: await progress_message.edit(content=f"⚠️ **Could not generate subtitles.**")
        return base_clip_path
    async def run_full_process(self, source_video_name, start_clip_index=0, num_to_process=None):
        channel = self.bot.get_channel(int(self.cog.config['bot']['channel_id'])); source_video_path = os.path.join(utils.INPUT_VIDEOS_DIR, source_video_name)
        if num_to_process is None:
            _, num_to_process = await self.prompt_for_clips(channel, source_video_path)
            if num_to_process is None: return
        if self.is_online and start_clip_index == 0:
            playlist_title = Path(source_video_name).stem.replace('_', ' ').replace('.', ' ').title()
            playlist_id = await helpers.create_youtube_playlist(self.cog.youtube, playlist_title)
            if not playlist_id: await channel.send("❌ Failed to create playlist."); return
            await self.cog._log_quota_usage('playlist_insert')
            self.cog.progress['source_videos'][source_video_name] = {'status': 'processing', 'playlist_id': playlist_id, 'clips': {}}
            utils.save_progress(self.cog.progress)
        await channel.send(f"⚙️ Starting processing of **{num_to_process}** clips...")
        for i in range(start_clip_index, start_clip_index + num_to_process):
            clip_number = i + 1; clip_path = await self.create_clip(channel, source_video_path, clip_number)
            if clip_path:
                clip_filename = os.path.basename(clip_path)
                self.cog.progress['source_videos'][source_video_name]['clips'][clip_filename] = {'status': 'pending_upload', 'created_at': datetime.now(timezone.utc).isoformat()}
            else:
                self.cog.progress['source_videos'][source_video_name]['status'] = 'failed_split'; break
        utils.save_progress(self.cog.progress)
        await channel.send(f"✅ Batch processing complete! **{num_to_process}** clips added to upload queue.")
        total_possible = await self.get_total_clips(source_video_name)
        if total_possible and len(self.cog.progress['source_videos'][source_video_name]['clips']) >= total_possible:
            if self.is_online: self.cog.progress['source_videos'][source_video_name]['status'] = 'completed'
            shutil.move(source_video_path, os.path.join(utils.PROCESSED_VIDEOS_DIR, source_video_name))
            await channel.send(f"✅ **All processing for `{source_video_name}` is complete!**")
        else: await channel.send(f"✅ Batch complete. `{source_video_name}` remains in progress.")
        utils.save_progress(self.cog.progress)
    async def get_total_clips(self, source_video_name):
        source_video_path = os.path.join(utils.INPUT_VIDEOS_DIR, source_video_name); duration = await asyncio.to_thread(utils.get_video_duration, source_video_path)
        if not duration:
            logging.error(f"🚨 Unreadable file: '{source_video_name}'."); quarantine_path = os.path.join(utils.QUARANTINED_VIDEOS_DIR, source_video_name)
            shutil.move(source_video_path, quarantine_path); logging.info(f"   -> Moved to quarantine.")
            channel = self.bot.get_channel(int(self.cog.config['bot']['channel_id']))
            if channel: await channel.send(f"🚨 **Warning:** Could not read `{source_video_name}`. Moved to quarantine.")
            return None
        clip_duration = self.cog.config['video']['clip_duration_seconds']; overlap = self.cog.config['video']['clip_overlap_seconds']
        return int(duration / (clip_duration - overlap)) or 1
    async def prompt_for_clips(self, channel, source_video_path):
        source_video_name = os.path.basename(source_video_path); total_clips = await self.get_total_clips(source_video_name)
        if total_clips is None: return None, None
        await channel.send(f"🎬 **New video:** `{source_video_name}` | **{total_clips}** clips possible.\n> How many to process?")
        try:
            def check(m): return m.channel == channel and (m.content.lower() == 'all' or (m.content.isdigit() and 1 <= int(m.content) <= total_clips))
            msg = await self.bot.wait_for('message', timeout=self.cog.config['bot']['prompt_timeout_minutes'] * 60.0, check=check)
            num_to_process = total_clips if msg.content.lower() == 'all' else int(msg.content); await channel.send(f"✅ OK! Processing **{num_to_process}** clip(s).")
            return total_clips, num_to_process
        except asyncio.TimeoutError: return None, None