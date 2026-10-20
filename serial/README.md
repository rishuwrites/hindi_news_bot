# Serial recap channel (Dangal TV shows -> 2-3 min "motion comic" recaps)
Folder: serial/ ; workflow: .github/workflows/serial.yml ; state: serial/state/<show>.json
Secrets (use a SEPARATE Google Cloud project + token for this channel): YT2_CLIENT_ID, YT2_CLIENT_SECRET, YT2_REFRESH_TOKEN, GEMINI_API_KEY
Optional: YT_API_KEY (YouTube Data API key: lets the bot see the channel's last 50 uploads instead of 15), CF_ACCOUNT_ID + CF_API_TOKEN (Cloudflare Workers AI, more reliable images),
POLLINATIONS_TOKEN, variable SERIAL_CHANNEL_NAME (name shown on screen), SERIAL_VOICE (default hi-IN-SwaraNeural).
Music: put your own royalty-free .mp3 tracks in serial/music/ (one is picked at random, played at low volume). No tracks = no music.
Manual run: Actions > serial-recaps > Run workflow (pick a show, optional video_id, test_mode = 3 scenes without upload).
