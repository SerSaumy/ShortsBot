# ShortsBot Command Reference

This file lists all the available commands to control the ShortsBot via Discord.

---

## Main Commands

These are the primary commands for controlling the bot's processing loop.

*   `!start`
    *   Starts the main processing loop.
    *   The bot will begin scanning the `input_videos` folder for new files to process.
    *   Can only be used when processing is stopped.

*   `!stop`
    *   Stops the main processing loop gracefully.
    *   The bot will finish any clip it is currently creating or uploading and will then halt. It will not start any new tasks.
    *   Can only be used when processing is active.

*   `!status`
    *   Shows the current status of the bot.
    *   It will tell you if the bot is `ACTIVE`, `STOPPED`, or `WAITING FOR USER INPUT`.

*   `!end`
    *   Shuts down the entire bot program completely.
    *   This is equivalent to stopping the `python main.py` script from the terminal.
    *   You will need to restart the bot from the terminal after using this command.

*   `!quota`
    *   Displays the current estimated YouTube API quota usage for the day.
    *   This provides a real-time estimate of how many API units you have left.


---

## Developer Commands

These commands are intended for development and maintenance.

*   `!reload`
    *   **Owner Only:** This command can only be used by the person whose User ID is set as `owner_id` in `config.yaml`.
    *   Reloads all the bot's code modules (`utils.py`, `helpers.py`, `bot_cog.py`) without a full restart.
    *   Use this command after you have saved changes to the code to make them take effect immediately.