# ShortsBot: An Automated Video Content Pipeline

Welcome to ShortsBot! This is a powerful, fully automated Python application designed to streamline your content creation process. It monitors a folder for new videos, intelligently splits them into short clips, automatically generates and burns in word-for-word subtitles, and schedules them for upload to your YouTube channel, all controlled via simple Discord commands.

This project is built with a focus on reliability and deterministic operation, utilizing a suite of powerful, industry-standard tools without reliance on non-deterministic AI for its core logic.

---

## Table of Contents

-   [Key Features](#-key-features)
-   [System Architecture](#-system-architecture)
-   [Installation & Configuration](#️-installation--configuration)
    -   [Prerequisites](#step-1-prerequisites)
    -   [Project Setup](#step-2-project-setup)
    -   [Google Cloud & YouTube API Configuration](#step-3-google-cloud--youtube-api-configuration)
    -   [Discord Bot Configuration](#step-4-discord-bot-configuration)
    -   [Final Application Configuration](#step-5-final-application-configuration)
-   [Usage Guide](#-usage-guide)
-   [Folder Structure](#-folder-structure)
-   [License](#-license)

---

## 🌟 Key Features

-   **Automated Processing Pipeline:** Monitors an input directory and processes new video files end-to-end.
-   **Intelligent Video Clipping:** Splits source videos into configurable-length clips with overlap support for seamless viewing.
-   **Automatic Subtitles:** Uses a local `openai-whisper` model to generate highly accurate, time-synced subtitles and burns them onto the video clips.
-   **Full YouTube Integration:**
    -   Automatically creates public playlists for each new video series.
    -   Uploads clips as private and schedules them for publication according to a customizable weekly timetable.
    -   Associates each clip with its corresponding playlist.
-   **Robust State Management:**
    -   Maintains a persistent `progress.json` state file to prevent duplicate processing and allow for safe resumption of incomplete jobs.
    -   Intelligently prioritizes tasks: `Failed Uploads` > `Pending Uploads` > `In-Progress Videos` > `New Videos`.
    -   Automatically quarantines corrupted video files to ensure pipeline integrity.
-   **Comprehensive Discord Control:**
    -   Full operational control via commands (`!start`, `!stop`, `!end`).
    -   Real-time status monitoring (`!status`), API quota checks (`!quota`), and schedule previews (`!schedule`).
    -   Preview a video's clipping plan before processing (`!preview`).
-   **Offline "Dry Run" Mode:** A configuration switch to run the entire video processing and subtitling pipeline locally for testing, without consuming any YouTube API quota.

## 🏗️ System Architecture

ShortsBot operates as a stateful, asynchronous application. It leverages `asyncio` for concurrent operations and is structured into modular components for maintainability:

-   **Core Logic (`workflows.py`):** The "brain" of the bot, managing the state machine and processing pipeline.
-   **Discord Interface (`bot_cog.py`):** Handles all user commands and feedback within Discord.
-   **API Helpers (`helpers.py`):** Manages all communication with the YouTube Data API v3.
-   **Video Utilities (`utils.py`):** Contains FFmpeg commands for video splitting and formatting.
-   **Subtitle Engine (`subtitles.py`):** Integrates Whisper for transcription and MoviePy/ImageMagick for rendering text onto video.

## 🛠️ Installation & Configuration

This guide provides a detailed walkthrough for setting up ShortsBot on a Windows environment.

### Step 1: Prerequisites

Ensure the following system-level dependencies are installed and configured:

1.  **Python (3.10+):** Download from [python.org](https://www.python.org/downloads/). During installation, ensure you check the box to "Add Python to PATH".
2.  **Git:** Download from [git-scm.com](https://git-scm.com/).
3.  **FFmpeg:** Essential for all video operations.
    -   Download the latest "release full build" from a trusted source like [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
    -   Extract the archive to a permanent location (e.g., `C:\ffmpeg`).
    -   **Crucially, add the `bin` sub-directory** (e.g., `C:\ffmpeg\bin`) to your Windows System PATH environment variables.
4.  **ImageMagick:** Required by MoviePy for rendering text.
    -   Download and install the latest version from [imagemagick.org](https://imagemagick.org/script/download.php).
    -   During installation, **you must check the box "Add application directory to your system path"**.

*After installing FFmpeg and ImageMagick, it is highly recommended to **restart your computer** to ensure the PATH changes are applied system-wide.*

### Step 2: Project Setup

1.  **Clone the Repository:** Open your terminal (Command Prompt or PowerShell) and navigate to where you want to store the project.
    ```bash
    git clone https://github.com/sersaumy/ShortsBot.git
    cd ShortsBot
    ```
2.  **Install Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

### Step 3: Google Cloud & YouTube API Configuration

This process authorizes the application to act on your YouTube channel's behalf.

1.  Navigate to the [Google Cloud Console](https://console.cloud.google.com/) and create a **New Project**.
2.  Search for and **Enable** the **"YouTube Data API v3"**.
3.  From the navigation menu, go to **APIs & Services > OAuth consent screen**.
    -   Select **External** and create the screen.
    -   Provide an App name (e.g., "ShortsBot Automation"), your email address, and save.
    -   Click "Save and Continue" to go to the "Scopes" page (you can leave this blank).
    -   **CRITICAL STEP:** On the **"Test users"** page, click **+ ADD USERS**. Add the Google Account email address associated with the YouTube channel you want to upload to. You can add multiple accounts if you plan to switch between them. Your app will only work for these specified accounts until it is officially published (which is not necessary for this project).
4.  Navigate to **APIs & Services > Credentials**.
    -   Click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
    -   Set the Application type to **Desktop app**.
    -   Click **Create**.
5.  A window will appear. Click **DOWNLOAD JSON**.
6.  Rename this downloaded file to **`client_secrets.json`** and place it in the root `ShortsBot` folder.

### Step 4: Discord Bot Configuration

This allows the bot to connect to Discord and receive your commands.

1.  Navigate to the [Discord Developer Portal](https://discord.com/developers/applications) and create a **New Application**.
2.  In the **Bot** tab, click **Reset Token** to get your bot's secret token. Copy and save it securely.
3.  Enable the **MESSAGE CONTENT INTENT** under "Privileged Gateway Intents".
4.  Go to the **OAuth2 > URL Generator** tab. Select the `bot` scope. In the permissions that appear, select `Send Messages` and `Read Message History`.
5.  Copy the generated URL, paste it into your browser, and invite the bot to your server.
6.  **Enable Developer Mode** in your Discord client (User Settings > Advanced).
    -   **To get the Channel ID:** Right-click your target text channel and select **"Copy Channel ID"**.
    -   **To get your User ID:** Right-click your own username and select **"Copy User ID"**. This is required for owner-only commands like `!reload`.

### Step 5: Final Application Configuration

1.  **Create Config Files:**
    -   In the `ShortsBot` folder, rename `config.template.yaml` to **`config.yaml`**.
    -   Rename `schedule.template.yaml` to **`schedule.yaml`**.
2.  **Edit `config.yaml`:** Open the file and meticulously fill in all placeholder values, paying close attention to indentation (use spaces, not tabs).
    -   `discord_token`, `channel_id`, `owner_id`.
    -   The full, absolute path to your `magick.exe` file (use forward slashes `/`).
3.  **Add a Font:** Place at least one `.ttf` or `.otf` font file inside the `/fonts/` directory. Update the `font_filename` in `config.yaml` to match the exact filename of the font you wish to use.

## 🚀 Usage Guide

1.  **First Run & Authorization:**
    -   Ensure `youtube_online_mode` is `true` in `config.yaml`.
    -   Run the bot from your terminal: `python main.py`
    -   A browser window will open. **Authorize the application by logging into the Google Account you added as a "Test User"**. A `token.json` file will be created, completing the authorization.
2.  **Normal Operation:**
    -   Start the bot: `python main.py`
    -   Wait for the "✅ ShortsBot is online and ready!" message in Discord.
    -   Drop a video file into the `/input_videos/` folder.
    -   The bot will automatically check for work every few minutes. To trigger an immediate check for new source videos, use the `!start` command.

Refer to `COMMANDS.md` for a full list of available commands and their functions.

## 🗂️ Folder Structure

-   `/input_videos/`: Drop your source `.mp4`/`.mkv` files here.
-   `/processed_clips/`: Final, subtitled clips are stored here.
-   `/processed_videos/`: Source videos are moved here after being fully processed.
-   `/failed_uploads/`: Clips that fail to upload are moved here for a retry.
-   `/quarantined_videos/`: Corrupted source videos are moved here for manual inspection.
-   `/fonts/`: Place your `.ttf`/`.otf` font files for subtitles here.
-   `/logs/`: Contains daily log files of the bot's activity.
-   `progress.json`: The bot's "memory". Tracks the status of all videos and clips.

## ⚖️ License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
