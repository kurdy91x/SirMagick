import asyncio
from dataclasses import dataclass, field
import logging
import shutil
from pathlib import Path
import sys
from time import monotonic
from uuid import uuid4

import discord

from .bot_commands import find_image, parse_command
from .downloads import create_download_session, download_image
from .worker import ProcessWorker
from .effects import DESCRIPTIONS

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

SLASH_PREFIX = "sm_"

HELP = (
    "**SirMagick – image effects**\n"
    "`/sm_blockface` – shrink the inner face and stretch the surrounding skin\n"
    "`/sm_warpface` – enlarge the head and shrink facial features\n"
    "`/sm_chudthor` – surreal, angular face distortion\n"
    "`/sm_deepfry` – extreme colors, JPEG artifacts, and random stickers\n"
    "**Face:** `/sm_fatmagic`, `/sm_tinyface`, `/sm_bigmouth`, `/sm_googly`, `/sm_eyeswap`\n"
    "**Ultrawide:** `/sm_wide` – stretch the image to triple width\n"
    "**Retro:** `/sm_glitch`, `/sm_crt`, `/sm_halftone`\n"
    "**Fractal:** `/sm_julia`, `/sm_newton`\n"
    "**Depth:** `/sm_extrude`, `/sm_emboss`\n"
    "**Typography:** `/sm_numbers`, `/sm_letters`\n"
      "**Neon:** `/sm_tron`\n"
      "**Rift:** `/sm_rift`\n"
      "**Cinematic:** `/sm_thermal`, `/sm_nightvision`, `/sm_thanos`, `/sm_dealwithit`\n"
    "**Face fantasy:** `/sm_halo`, `/sm_devilhorns`\n"
    "**Vortex:** `/sm_vortexcolumns`, `/sm_eyevortex`, `/sm_mouthvortex`\n"
    "**Lens:** `/sm_fisheye`\n"
    "**Trippy:** `/sm_zoom`, `/sm_tunnel`, `/sm_kaleidoscope`, `/sm_swirl`, `/sm_rgbghost`\n"
    "**Euler:** `/sm_droste`, `/sm_complexsquare`, `/sm_complexexp`, `/sm_logpolar`, `/sm_inversion`\n"
    "**Anime:** `/sm_uwu`, `/sm_blush`, `/sm_sweat`, `/sm_sparkle`, `/sm_angry`\n"
    "`/sm_random` – random effect; `/sm_help` – this help\n\n"
    "Upload an **image** or provide a **url** with any effect. "
    "Leave both empty to use the latest channel image, including previous bot results. "
    "All detected faces are processed. GIFs use the first frame.\n"
    "You can also use `@SirMagick blockface` or `@SirMagick help`."
)


class InteractionMessage:
    """Expose slash requests to the same queue and history selection as mentions."""
    def __init__(self, interaction, content, attachment=None):
        self.interaction = interaction
        self.id = interaction.id
        self.author = interaction.user
        self.guild = interaction.guild
        self.channel = interaction.channel
        self.content = content
        self.attachments = [attachment] if attachment else []
        self.embeds = []
        self.first_reply = True

    async def reply(self, content=None, **kwargs):
        kwargs.pop("mention_author", None)
        kwargs["allowed_mentions"] = discord.AllowedMentions.none()
        if self.first_reply:
            self.first_reply = False
            return await self.interaction.followup.send(content, wait=True, **kwargs)
        # Results use normal channel messages, so queued jobs do not depend on
        # the interaction token still being valid when their processing ends.
        return await self.channel.send(content, **kwargs)


@dataclass
class Job:
    message: object
    command: object
    status: object = None
    ready: asyncio.Event = field(default_factory=asyncio.Event)


class MagickBot(discord.Client):
    def __init__(self, config):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.config = config
        self.jobs = asyncio.Queue(maxsize=config.queue_size)
        self.cooldowns = {}
        self.pending = set()
        self.worker = ProcessWorker()
        self.consumer = None
        self.downloads = None
        self.tree = discord.app_commands.CommandTree(self)
        self.tree.on_error = self.slash_error
        self.guild_sync_attempted = set()
        self.guild_sync_lock = asyncio.Lock()
        self.register_commands()

    def allowed(self, guild, channel):
        return bool(guild and channel
                    and (not self.config.guild_ids or guild.id in self.config.guild_ids)
                    and (not self.config.channel_ids or channel.id in self.config.channel_ids))

    def register_commands(self):
        descriptions = DESCRIPTIONS

        def effect_command(effect):
            @discord.app_commands.describe(image="Upload an image; otherwise use the latest channel image",
                                           url="Alternatively, provide a public image URL")
            async def callback(interaction: discord.Interaction,
                               image: discord.Attachment | None = None, url: str | None = None):
                LOGGER.info("Slash command: /%s | Guild ID %s | Channel ID %s", SLASH_PREFIX+effect,
                            interaction.guild_id, interaction.channel_id)
                if not self.allowed(interaction.guild, interaction.channel):
                    await interaction.response.send_message("The bot is not enabled here.", ephemeral=True)
                    return
                if image and url:
                    await interaction.response.send_message("Provide either an image or a URL, not both.", ephemeral=True)
                    return
                await interaction.response.defer(thinking=True)
                content = f"<@{self.user.id}> {effect}" + (f" {url}" if url else "")
                await self.on_message(InteractionMessage(interaction, content, image))
            return discord.app_commands.Command(name=SLASH_PREFIX+effect, description=descriptions[effect], callback=callback)

        for effect in descriptions:
            self.tree.add_command(discord.app_commands.guild_only()(effect_command(effect)))

        @self.tree.command(name=SLASH_PREFIX+"help", description="List all image effects and how to use them")
        @discord.app_commands.guild_only()
        async def help_command(interaction: discord.Interaction):
            LOGGER.info("Slash command: /sm_help | Guild ID %s | Channel ID %s",
                        interaction.guild_id, interaction.channel_id)
            if not self.allowed(interaction.guild, interaction.channel):
                await interaction.response.send_message("The bot is not enabled here.", ephemeral=True)
                return
            await interaction.response.send_message(HELP, ephemeral=True)

    async def setup_hook(self):
        # Sync once at startup, never on reconnect. Failure is visible in the
        # console while existing mention commands remain usable.
        LOGGER.info("Bot source: %s | Python: %s", Path(__file__).resolve(), sys.executable)
        await self.sync_commands()
        self.config.work.mkdir(parents=True, exist_ok=True)
        self.downloads = create_download_session(self.config.download_timeout)
        self.consumer = asyncio.create_task(self.consume())

    async def sync_commands(self):
        LOGGER.info("Registering %d slash commands with Discord (Application ID: %s) …",
                    len(self.tree.get_commands()), self.application_id)
        try:
            async with asyncio.timeout(30):
                commands = await self.tree.sync()
            LOGGER.info("Discord confirmed %d global slash commands: %s", len(commands),
                        ", ".join("/" + command.name for command in commands))
        except discord.HTTPException as exc:
            LOGGER.warning("Slash registration failed: HTTP %s, Discord code %s. "
                           "Check the bot invitation and applications.commands scope.", exc.status, exc.code)
        except TimeoutError:
            LOGGER.warning("Slash registration: no response within 30 seconds.")

    async def sync_guild_commands(self, guild):
        if self.config.guild_ids and guild.id not in self.config.guild_ids:
            return
        async with self.guild_sync_lock:
            if guild.id in self.guild_sync_attempted:
                return
            self.guild_sync_attempted.add(guild.id)
            # Replace the entire guild catalog, including any legacy names.
            self.tree.clear_commands(guild=guild)
            self.tree.copy_global_to(guild=guild)
            try:
                async with asyncio.timeout(30):
                    commands = await self.tree.sync(guild=guild)
                LOGGER.info("Discord confirmed %d slash commands directly in guild %s (%s).",
                            len(commands), guild.name, guild.id)
            except discord.HTTPException as exc:
                LOGGER.warning("Guild slash registration failed for %s: HTTP %s, Discord code %s. "
                               "Check the guild installation with bot and applications.commands scopes.",
                               guild.id, exc.status, exc.code)
            except TimeoutError:
                LOGGER.warning("Guild slash registration for %s timed out.", guild.id)

    async def slash_error(self, interaction, error):
        LOGGER.warning("Slash command failed: %s | Guild ID %s | Channel ID %s",
                       type(error).__name__, interaction.guild_id, interaction.channel_id)
        text = "Slash command failed. Use @sirmagick help and check the bot console."
        try:
            async with asyncio.timeout(self.config.upload_timeout):
                if interaction.response.is_done():
                    await interaction.followup.send(text, ephemeral=True)
                else:
                    await interaction.response.send_message(text, ephemeral=True)
        except (discord.HTTPException, TimeoutError):
            LOGGER.warning("Could not send the slash command error message.")

    async def on_guild_join(self, guild):
        await self.sync_guild_commands(guild)

    async def on_ready(self):
        LOGGER.info("Connected as %s (Bot ID: %s), available in %d guilds. "
                    "Channel help: @%s help", self.user, self.user.id, len(self.guilds), self.user.name)
        LOGGER.info("Guild filter: %s | Channel filter: %s | Message content intent in code: %s",
                    sorted(self.config.guild_ids) or "all", sorted(self.config.channel_ids) or "all",
                    self.intents.message_content)
        for guild in self.guilds:
            await self.sync_guild_commands(guild)

    async def close(self):
        if self.consumer:
            self.consumer.cancel()
            try:
                await self.consumer
            except asyncio.CancelledError:
                pass
        await self.worker.close()
        if self.downloads:
            await self.downloads.close()
        await super().close()

    async def reply(self, message, text=None, **kwargs):
        async with asyncio.timeout(self.config.upload_timeout):
            return await message.reply(text, mention_author=False, **kwargs)

    async def status(self, job, text):
        try:
            async with asyncio.timeout(self.config.upload_timeout):
                if job.status:
                    await job.status.edit(content=text)
                else:
                    await self.reply(job.message, text)
        except (discord.HTTPException, TimeoutError):
            logging.warning("Could not send the status message.")

    async def on_message(self, message):
        cfg = self.config
        if message.author.bot or not message.guild or not self.user:
            return
        if not self.allowed(message.guild, message.channel):
            if message.content.lstrip().lower().startswith(("@sirmagick", f"<@{self.user.id}>", f"<@!{self.user.id}>")):
                LOGGER.warning("Command ignored by filters: Guild ID %s, Channel ID %s.",
                               message.guild.id, message.channel.id)
            return
        try:
            command = parse_command(message.content, self.user.id)
            if command is None:
                return
            LOGGER.info("Command received: %s | Guild ID %s | Channel ID %s", command.effect,
                        message.guild.id, message.channel.id)
            if command.effect == "help":
                await self.reply(message, HELP)
                return
            now = monotonic()
            self.cooldowns = {key: expiry for key, expiry in self.cooldowns.items() if expiry > now}
            user = message.author.id
            if user in self.pending or user in self.cooldowns:
                raise ValueError("Please wait before submitting another image.")
            job = Job(message, command)
            try:
                self.jobs.put_nowait(job)
            except asyncio.QueueFull:
                raise ValueError("The queue is full. Please try again later.") from None
            self.pending.add(user)
            self.cooldowns[user] = now + cfg.cooldown
            try:
                job.status = await self.reply(message, "Image job accepted.")
            finally:
                job.ready.set()
        except ValueError as exc:
            await self.reply(message, str(exc))
        except discord.HTTPException as exc:
            LOGGER.warning("Command response failed: HTTP %s, Discord code %s. "
                           "Check Send Messages and channel permissions.", exc.status, exc.code)
        except TimeoutError:
            LOGGER.warning("Sending the command response timed out.")

    async def consume(self):
        cfg = self.config
        while True:
            job = await self.jobs.get()
            directory = cfg.work / uuid4().hex
            stage = "setup"
            try:
                await job.ready.wait()
                await self.status(job, "Processing image …")
                directory.mkdir()
                async with asyncio.timeout(cfg.download_timeout):
                    stage = "image lookup"
                    url = job.command.url or await find_image(job.message, cfg.history_limit, cfg.max_download)
                    source = directory / "input"
                    stage = "download"
                    await download_image(self.downloads, url, source, cfg.max_download, cfg.download_timeout)
                stage = "processing"
                output = await self.worker.run({
                    "effect": job.command.effect, "source": str(source),
                    "destination": str(directory / "result"), "models": str(cfg.models),
                    "max_side": cfg.max_side, "max_people": cfg.max_people,
                    "max_output": min(cfg.max_output, job.message.guild.filesize_limit),
                }, cfg.process_timeout)
                attachment = discord.File(output, filename=output.name)
                try:
                    stage = "upload"
                    label = job.command.effect
                    if label == "random" and "-random-" in output.stem:
                        label = "random → " + output.stem.split("-random-", 1)[1]
                    await self.reply(job.message, label, file=attachment)
                finally:
                    attachment.close()
                await self.status(job, "Done.")
            except TimeoutError:
                await self.status(job, "Time limit reached. Job aborted.")
            except ValueError as exc:
                await self.status(job, str(exc))
            except discord.HTTPException as exc:
                LOGGER.warning("Image job failed during %s: effect=%s guild=%s channel=%s "
                               "HTTP=%s Discord code=%s; continuing the queue.",
                               stage, job.command.effect, getattr(job.message.guild, 'id', None),
                               getattr(getattr(job.message, 'channel', None), 'id', None), exc.status, exc.code)
                if exc.status == 403:
                    permission = "View Channel and Read Message History" if stage == "image lookup" else (
                        "Send Messages, Attach Files, and Send Messages in Threads (for threads)"
                        if stage == "upload" else "View Channel and Send Messages")
                    await self.status(job, f"Missing Discord permissions during {stage}. Check {permission} in this channel, including role/category overrides.")
                elif exc.status == 413 or exc.code == 40005:
                    await self.status(job, "Discord rejected the upload as too large for this server.")
                else:
                    await self.status(job, f"Discord request failed during {stage} (HTTP {exc.status}, code {exc.code}).")
            except Exception as exc:
                LOGGER.warning("Image job failed during %s: effect=%s guild=%s exception=%s; "
                               "continuing the queue.", stage, job.command.effect,
                               getattr(job.message.guild, 'id', None), type(exc).__name__)
                message = ("Image worker stopped unexpectedly. Check container memory limits and server logs."
                           if stage == "processing" and isinstance(exc, RuntimeError)
                           else f"Job failed during {stage} ({type(exc).__name__}). Check the server logs.")
                await self.status(job, message)
            finally:
                self.pending.discard(job.message.author.id)
                self.jobs.task_done()
                if directory.exists() and directory.resolve().parent == cfg.work.resolve():
                    try:
                        shutil.rmtree(directory)
                    except OSError:
                        logging.warning("Could not remove job files.")


def run_bot():
    from dotenv import load_dotenv
    from .bot_config import BotConfig
    load_dotenv(override=False)
    config = BotConfig.from_env()
    logging.basicConfig(level=logging.WARNING)
    MagickBot(config).run(config.token, log_handler=None)
