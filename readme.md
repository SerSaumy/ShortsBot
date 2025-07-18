# ShortsBot - Automated YouTube Shorts Pipeline

ShortsBot is a Python-based automation tool for creating and uploading YouTube Shorts from long-form video content. It is controlled via a Discord bot and is designed to be a fully deterministic, non-AI system.

## Features

- **Folder Monitoring:** Automatically detects new videos in a target folder.
- **Video Splitting & Formatting:** Splits videos into clips of configurable duration with overlap and formats them into a vertical, center-stage layout.
- **Automatic Subtitles:** Uses a local `openai-whisper` model to transcribe and burn styled, word-for-word subtitles onto each clip.
- **YouTube Integration:**
  - Creates a new playlist for each source video.
  - Uploads clips as Shorts to a specified channel.
  - Schedules uploads according to a customizable weekly timetable.
  - Adds clips to the correct playlist.
- **Robust State Management:**
  - Remembers all progress to avoid duplicate work and resume incomplete jobs.
  - Intelligently prioritizes tasks: failed uploads > pending uploads > in-progress videos > new videos.
  - Gracefully handles corrupted video files by quarantining them.
- **Discord Control:** Fully controllable via Discord commands (`!start`, `!stop`, `!status`, `!quota`, `!schedule`, `!preview`, `!reload`).
- **Offline Mode:** Includes a "Dry Run" mode to test the entire video processing pipeline locally without touching the YouTube API.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/ShortsBot.git
    cd ShortsBot
    ```

2.  **Install Dependencies:**
    -   Install Python 3.10+.
    -   Install system dependencies: **FFmpeg** and **ImageMagick**. Ensure they are added to your system's PATH.
    -   Install the required Python packages:
        ```bash
        pip install -r requirements.txt
        ```

3.  **Configure the Bot:**
    -   Rename `config.template.yaml` to `config.yaml`.
    -   Open `config.yaml` and fill in all the required values, especially your Discord bot token, channel/owner IDs, and the full path to your ImageMagick executable.
    -   Rename `schedule.template.yaml` to `schedule.yaml` and customize the weekly schedule as needed.
    -   Place a `.ttf` or `.otf` font file inside the `/fonts/` directory and update the `font_filename` in `config.yaml`.

4.  **Google API Credentials:**
    -   Follow the Google Cloud Console instructions to create an **OAuth 2.0 Client ID** for a "Desktop app".
    -   Download the credentials file and rename it to `client_secrets.json` in the project root.

5.  **Run the Bot:**
    -   The first time you run the bot in online mode, it will open a browser window to ask you to authorize its access to your YouTube account.
    ```bash
    python main.py
    ```