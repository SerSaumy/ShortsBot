# -----------------------------------------------------------------------------
# ShortsBot Subtitle Generation Module - COMPLETE MOVIEPY VERSION
# -----------------------------------------------------------------------------
import asyncio
import logging
import os
from moviepy.config import change_settings
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip

WHISPER_MODEL = None
MOVIEPY_CONFIGURED = False

def configure_moviepy(imagemagick_path: str):
    """Explicitly tells MoviePy where to find the ImageMagick binary."""
    global MOVIEPY_CONFIGURED
    if MOVIEPY_CONFIGURED: return
    if not os.path.exists(imagemagick_path):
        logging.warning(f"⚠️ ImageMagick path not found: {imagemagick_path}. Subtitles may fail.")
        return
    try:
        change_settings({"IMAGEMAGICK_BINARY": imagemagick_path})
        MOVIEPY_CONFIGURED = True
        logging.info("✅ MoviePy configuration updated successfully.")
    except Exception as e: logging.error(f"❌ Failed to configure MoviePy path: {e}")

def load_whisper_model(model_name="base"):
    """Loads a specified Whisper model into memory."""
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        try:
            import whisper; WHISPER_MODEL = whisper.load_model(model_name)
            logging.info(f"✅ Whisper model '{model_name}' loaded.")
        except Exception as e:
            logging.error(f"❌ Failed to load Whisper model: {e}"); WHISPER_MODEL = "failed"
    return WHISPER_MODEL

async def generate_subtitles(video_path: str) -> str | None:
    """Takes a video file path, transcribes it, and returns the path to a sanitized .srt file."""
    if WHISPER_MODEL == "failed" or WHISPER_MODEL is None: return None
    base_name_no_spaces = os.path.splitext(os.path.basename(video_path))[0].replace(' ', '_')
    srt_filename = f"{base_name_no_spaces}.srt"
    srt_path = os.path.join(os.path.dirname(video_path), srt_filename)
    logging.info(f"🎤 Transcribing: {os.path.basename(video_path)}")
    try:
        import whisper; result = await asyncio.to_thread(WHISPER_MODEL.transcribe, video_path, fp16=False, word_timestamps=True)
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            word_index = 1
            for segment in result['segments']:
                for word in segment['words']:
                    start, end, text = word['start'], word['end'], word['word'].strip()
                    start_srt = f"{int(start//3600):02}:{int(start%3600//60):02}:{int(start%60):02},{int(start%1*1000):03}"
                    end_srt = f"{int(end//3600):02}:{int(end%3600//60):02}:{int(end%60):02},{int(end%1*1000):03}"
                    srt_file.write(f"{word_index}\n{start_srt} --> {end_srt}\n{text}\n\n")
                    word_index += 1
        logging.info(f"✅ Subtitles generated: {os.path.basename(srt_path)}"); return srt_path
    except Exception as e:
        logging.error(f"❌ Whisper transcription failed: {e}", exc_info=True)
        if os.path.exists(srt_path): os.remove(srt_path)
        return None

async def burn_subtitles_into_video(video_path: str, srt_path: str, font_path: str, style: dict) -> str | None:
    """Burns subtitles onto a video using the MoviePy library."""
    output_path = os.path.splitext(video_path)[0] + "_subtitled.mp4"
    logging.info(f"🔥 Burning subtitles into: {os.path.basename(video_path)} using MoviePy...")
    try:
        generator = lambda txt: TextClip(
            txt, font=font_path, fontsize=style.get("fontsize", 42),
            color=style.get("color", 'white'), stroke_color=style.get("stroke_color", 'black'),
            stroke_width=style.get("stroke_width", 2.0), method='caption', size=(1000, None)
        )
        def process_with_moviepy():
            video = VideoFileClip(video_path)
            subtitles = SubtitlesClip(srt_path, generator)
            result = CompositeVideoClip([video, subtitles.set_position(lambda t: ('center', 1500 - subtitles.get_frame(t).shape[0]))])
            result.write_videofile(output_path, audio_codec='aac', threads=4, logger=None)
            video.close(); result.close()
        await asyncio.to_thread(process_with_moviepy)
        logging.info(f"✅ Subtitles burned successfully: {os.path.basename(output_path)}")
        return output_path
    except Exception as e:
        logging.error(f"❌ MoviePy failed to burn subtitles: {e}", exc_info=True)
        return None