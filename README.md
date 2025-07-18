# ShortsBot - Your Automated YouTube Shorts Pipeline

Welcome to ShortsBot! This is a powerful, fully automated Python application designed to streamline your content creation process. It monitors a folder for new videos, intelligently splits them into short clips, automatically generates and burns in word-for-word subtitles, and schedules them for upload to your YouTube channel, all controlled via simple Discord commands.

This system is built to be deterministic and reliable, with no AI decision-making involved.

---

## 🌟 Core Features

-   **Folder Monitoring:** Automatically detects new `.mp4` or `.mkv` videos.
-   **Intelligent Clipping:** Splits long videos into short clips of a set duration with overlap.
-   **Automatic Subtitles:** Uses a local `openai-whisper` model to generate perfectly synced, word-by-word subtitles and burns them onto the video.
-   **Full YouTube Integration:**
    -   Creates a public playlist for each new video series.
    -   Uploads clips as private and schedules them according to a weekly timetable.
    -   Adds each clip to the correct playlist.
-   **Robust State Management:**
    -   Remembers all progress in `progress.json` to avoid duplicate work.
    -   Intelligently resumes partially completed videos.
    -   Prioritizes re-uploading failed clips before starting new work.
    -   Quarantines corrupted video files to keep the pipeline running.
-   **Comprehensive Discord Control:**
    -   Full control via commands like `!start`, `!stop`, `!status`, and more.
    -   On-demand status checks for your YouTube API quota (`!quota`) and upcoming video schedule (`!schedule`).
    -   Preview a video's clipping plan before processing (`!preview`).
-   **Offline "Dry Run" Mode:** Test the entire video processing and subtitling pipeline locally without consuming any API quota or uploading to YouTube.

---

## 🛠️ Installation and Setup Guide

Follow these steps precisely to get your ShortsBot running.

### Part 1: System Prerequisites

Before you begin, you must have the following software installed on your computer:

1.  **Python:** Version 3.10 or newer. You can get it from [python.org](https://www.python.org/downloads/).
2.  **Git:** For managing the code. You can get it from [git-scm.com](https://git-scm.com/).
3.  **FFmpeg:** This is essential for all video processing.
    -   Download the latest "release full build" from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
    -   Unzip the file.
    -   You **must** add the `bin` folder from inside the unzipped folder to your Windows System PATH.
4.  **ImageMagick:** This is required for rendering subtitles.
    -   Download and install from [imagemagick.org](https://imagemagick.org/script/download.php).
    -   During installation, on the "Select Additional Tasks" screen, you **must** check the box that says **"Add application directory to your system path"**.

### Part 2: Project Setup

1.  **Clone the Repository:** Open your terminal or command prompt and run:
    ```bash
    git clone https://github.com/your-username/ShortsBot.git
    cd ShortsBot
    ```

2.  **Install Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

### Part 3: API Credentials

This is the most detailed part. Follow each step carefully.

#### A. Google Cloud & YouTube API Setup

This gives the bot the "key" to talk to YouTube.

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/) and log in.
2.  Create a **New Project** (e.g., "My Shorts Uploader").
3.  In the search bar, find and **Enable** the **"YouTube Data API v3"**.
4.  Go to the **Credentials** tab on the left.
5.  Click **+ CREATE CREDENTIALS** -> **OAuth client ID**.
6.  If prompted, configure the **Consent Screen**:
    -   Choose **External** and click Create.
    -   Give it an App name (e.g., "ShortsBot").
    -   Enter your email for the support and developer contact fields.
    -   Click "Save and Continue" through all the steps. You don't need to add scopes or test users here.
7.  Go back to **Credentials** and create the OAuth ID again.
    -   Application type: **Desktop app**.
    -   Name: `ShortsBot Client` (or anything).
    -   Click **Create**.
8.  A window will pop up. Click the **DOWNLOAD JSON** button.
9.  Rename the downloaded file to **`client_secrets.json`** and place it in the root of your `ShortsBot` project folder.

#### B. Discord Bot Setup

This gives you the token to run the bot and the IDs to control it.

1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a **New Application**.
2.  Go to the **Bot** tab on the left.
3.  Click **"Reset Token"** to reveal your bot's token. **Copy this token immediately and save it.** This is your bot's password.
4.  Scroll down and enable the **MESSAGE CONTENT INTENT**. This is **required** for the bot to read your commands.
5.  Go to the **OAuth2 -> URL Generator** tab.
    -   In "Scopes", check the box for `bot`.
    -   In "Bot Permissions", check `Send Messages` and `Read Message History`.
    -   Copy the generated URL at the bottom, paste it into your browser, and invite the bot to your Discord server.
6.  **Get Your IDs:**
    -   In Discord, go to User Settings -> Advanced and enable **Developer Mode**.
    -   **Channel ID:** Right-click on the text channel you want the bot to operate in and click **"Copy Channel ID"**.
    -   **Owner ID:** Right-click on your own username in Discord and click **"Copy User ID"**.

### Part 4: Final Project Configuration

1.  **Rename Template Files:**
    -   Rename `config.template.yaml` to **`config.yaml`**.
    -   Rename `schedule.template.yaml` to **`schedule.yaml`**.

2.  **Edit `config.yaml`:**
    -   Open `config.yaml` and carefully fill in every placeholder value. Use a text editor like VS Code that understands YAML indentation (use spaces, not tabs).

| Section         | Key                 | Description                                                                                             |
| --------------- | ------------------- | ------------------------------------------------------------------------------------------------------- |
| **`youtube`**   | `youtube_online_mode` | `true` to upload to YouTube, `false` for local-only testing.                                            |
| **`subtitles`** | `font_filename`     | The exact filename of the `.ttf` or `.otf` font you placed in the `/fonts/` folder (e.g., `arial.ttf`). |
|                 | `imagemagick_path`  | The **full, absolute path** to your `magick.exe` file. Use forward slashes (e.g., `C:/.../magick.exe`).     |
| **`bot`**       | `discord_token`     | The secret token you copied from the Discord Developer Portal.                                          |
|                 | `channel_id`        | The ID of the Discord channel where the bot will listen for commands.                                   |
|                 | `owner_id`          | Your personal Discord User ID. This is required for the `!reload` command.                              |

3.  **Add a Font:**
    -   Find a `.ttf` or `.otf` font file on your computer.
    -   Copy it into the `ShortsBot/fonts/` folder.
    -   Make sure the `font_filename` in your config matches this file's name exactly.

### Part 5: Running the Bot

1.  **First Run (Authorization):**
    -   Open your terminal in the `ShortsBot` folder.
    -   Ensure `youtube_online_mode` is `true` in your config.
    -   Run the command: `python main.py`
    -   Your browser will open. **Log in to the YouTube/Google account you want to upload videos to.**
    -   Grant the permissions. A `token.json` file will be created. The bot is now authorized.

2.  **Normal Operation:**
    -   Start the bot with `python main.py`.
    -   Wait for the "✅ ShortsBot is online and ready!" message in Discord.
    -   Drop a video file into the `/input_videos/` folder.
    -   Use the `!start` command in your designated Discord channel to begin processing.
