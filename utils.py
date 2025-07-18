# -----------------------------------------------------------------------------
# ShortsBot Utility Functions - ASYNC SUBPROCESS FIX
# -----------------------------------------------------------------------------
import asyncio, os, json, logging, sys, re, subprocess
from datetime import datetime
import yaml
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)); LOGS_DIR = os.path.join(ROOT_DIR, "logs")
INPUT_VIDEOS_DIR = os.path.join(ROOT_DIR, "input_videos"); PROCESSED_CLIPS_DIR = os.path.join(ROOT_DIR, "processed_clips")
PROCESSED_VIDEOS_DIR = os.path.join(ROOT_DIR, "processed_videos"); FAILED_UPLOADS_DIR = os.path.join(ROOT_DIR, "failed_uploads")
QUARANTINED_VIDEOS_DIR = os.path.join(ROOT_DIR, "quarantined_videos"); CONFIG_FILE = os.path.join(ROOT_DIR, "config.yaml")
PROGRESS_FILE = os.path.join(ROOT_DIR, "progress.json")
def setup_folders():
    folders_to_create = [LOGS_DIR, INPUT_VIDEOS_DIR, PROCESSED_CLIPS_DIR, PROCESSED_VIDEOS_DIR, FAILED_UPLOADS_DIR, QUARANTINED_VIDEOS_DIR]
    for folder_path in folders_to_create: os.makedirs(folder_path, exist_ok=True)
def setup_logger():
    log_filename = f"{datetime.now().strftime('%Y-%m-%d')}.log"; log_filepath = os.path.join(LOGS_DIR, log_filename)
    log_format = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"); logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(log_format); logger.addHandler(console_handler)
        file_handler = logging.FileHandler(log_filepath, mode="a", encoding="utf-8"); file_handler.setFormatter(log_format); logger.addHandler(file_handler)
        logging.getLogger("discord").setLevel(logging.WARNING); logging.getLogger("googleapiclient").setLevel(logging.WARNING)
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding='utf-8') as f: return yaml.safe_load(f)
    except Exception as e: logging.error(f"❌ Error loading config.yaml: {e}"); sys.exit(1)
def load_progress():
    default_progress = {"source_videos": {}, "last_scheduled_time": None, "quota_tracker": {}}
    try:
        with open(PROGRESS_FILE, "r") as f:
            progress = json.load(f);
            for key, value in default_progress.items(): progress.setdefault(key, value)
            return progress
    except (FileNotFoundError, json.JSONDecodeError): return default_progress
def save_progress(progress_data):
    try:
        with open(PROGRESS_FILE, "w") as f: json.dump(progress_data, f, indent=2)
    except Exception as e: logging.error(f"❌ CRITICAL: Failed to save progress! Error: {e}")
def create_progress_bar(percentage, length=20):
    filled_length = int(length * percentage // 100); bar = '█' * filled_length + '─' * (length - filled_length)
    return f"[{bar}] {percentage:.1f}%"
def get_video_duration(video_path):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout)
    except Exception as e: logging.error(f"Error getting video duration for {video_path}: {e}"); return None

async def split_video_into_clip_with_progress(source_path, clip_number, start_time, duration, progress_callback=None):
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    output_filename = f"{base_name} part {clip_number}.mp4"
    output_path = os.path.join(PROCESSED_CLIPS_DIR, output_filename)
    if os.path.exists(output_path):
        if progress_callback: await progress_callback(100.0)
        return output_path
    video_filter = "crop=ih:ih,scale=1080:1080,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black"
    command = ['ffmpeg', '-y', '-progress', 'pipe:1', '-nostats', '-ss', str(start_time), '-i', source_path, '-t', str(duration), '-vf', video_filter, '-c:v', 'libx264', '-preset', 'fast', '-c:a', 'copy', output_path]
    
    process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    
    time_pattern = re.compile(r"out_time_ms=(\d+)")
    while process.returncode is None:
        if process.stdout is None: await asyncio.sleep(0.1); continue
        try:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
            if not line: break
            line = line.decode('utf-8', errors='ignore').strip()
            match = time_pattern.search(line)
            if match:
                processed_us = int(match.group(1)); percentage = min((processed_us / (duration * 1_000_000)) * 100, 100.0)
                if progress_callback: await progress_callback(percentage)
        except asyncio.TimeoutError: break
    
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        if progress_callback: await progress_callback(100.0)
        return output_path
    else:
        logging.error(f"❌ FFmpeg failed to split clip #{clip_number}.\n{stderr.decode('utf-8', errors='ignore')}")
        return None