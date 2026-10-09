# Running the Discord bot

1. Create a Python 3.12 virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   python -m pip --python .venv install -r requirements.txt
   .venv\Scripts\python.exe -m sirmagick download-models
   ```

2. Create an application and bot in the [Discord Developer Portal](https://discord.com/developers/applications). Enable **Bot → Privileged Gateway Intents → Message Content Intent**. Copy `.env.example` to `.env` and set `DISCORD_TOKEN`. Keep the token private; `.env` is excluded from Git and Docker builds.
3. Under **OAuth2 → URL Generator**, select `bot` and `applications.commands`. Grant **View Channels**, **Read Message History**, **Send Messages**, and **Attach Files**. Threads also require **Send Messages in Threads**. Invite the bot using the generated URL.
4. Optionally set comma-separated `ALLOWED_GUILD_IDS` and `ALLOWED_CHANNEL_IDS`. Empty values allow all accessible guilds or channels. Direct messages are ignored.
5. Start the bot:

   ```powershell
   .venv\Scripts\python.exe -m sirmagick bot
   ```

Face effects require the downloaded models. They load on the first face request and remain in the worker. This includes anime effects, `halo`, `devilhorns`, and face-textured `vortexcolumns`. `deepfry`, `wide`, Trippy, Euler, Retro, Fractal, and Depth effects work without face models.

## Commands

See [README.md](README.md) for the complete effect catalog. All effects support `/sm_effect` and `@SirMagick effect`. `/sm_help` displays help privately to the caller. Replies, descriptions, and logs are in English.

Each slash effect accepts optional `image` and `url` fields. Provide one, or leave both empty to use the latest channel image. Mention commands accept an attachment or a URL, for example `@SirMagick droste https://example.org/image.jpg`. An attachment takes priority; otherwise the bot searches up to 50 previous messages by default. Previous bot results are valid inputs, but bot messages do not trigger requests. GIFs use the first frame. Face effects process every detected face.

All slash commands use the `sm_` prefix, including `/sm_random` and `/sm_help`. Type `/sm_` to filter the list. Mention commands keep their short names. Synchronization replaces the old unprefixed commands in the global and allowed-guild scopes. Slash commands sync globally at startup and once directly in each allowed guild after connecting. Reconnects do not repeat guild registration. Restart after an update to register new commands or changed options. Check console confirmations and HTTP/Discord error codes. If commands are missing, check the `bot` and `applications.commands` invitation scopes, the user's **Use Application Commands** permission, and **Server Settings → Integrations → SirMagick** restrictions.

If visible commands do not respond, check that the Developer Portal has no unrelated **Interactions Endpoint URL** configured: this bot receives interactions over its Gateway connection. Look for `Slash command: /...` in the console. If absent, check the application configuration and which bot process is running. Mention commands work independently of slash registration.

## Queue and limits

One job runs at a time; up to ten more wait by default. Each user can have one pending or running job, with a five-second cooldown. Failed jobs are abandoned and the queue continues. Processing timeout kills the CPU worker; the next request starts a new one. Queued jobs are held in memory and lost on restart.

Downloads accept public HTTP(S) targets only, checking DNS addresses and redirects. The default download maximum is 25 MiB; decoded images are limited to 24 million pixels. PNG is preferred for results. Fully opaque images may fall back to JPEG if needed for upload; images are not resized to meet upload limits. Oversized results produce an error. The effective upload limit also respects the Discord guild limit.

All settings are listed in `.env.example`. Working images are deleted after each request; an abrupt process exit can leave local files in `.cache/jobs/`. Docker uses temporary storage under `/tmp/sirmagick/jobs`.

## Verification

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -q
```

For a live check, process a face with `/sm_blockface`, then process the result again. Submit a face-free image to a face effect, then a valid `/sm_deepfry` request: the failed request must not block the next one. Check `/sm_help`, the `image` and `url` options, and a group photo. Strong transformations such as `/sm_vortexcolumns` may prevent face detection on a later request. Live Discord checks require your own token and enabled Message Content Intent.
