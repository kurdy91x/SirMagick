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

HELP = (
    "**SirMagick – Bilder bearbeiten**\n"
    "`/blockface` – Gesicht innen verkleinern, äußeren Hautstreifen strecken\n"
    "`/warpface` – Kopf vergrößern und Gesichtszüge verkleinern\n"
    "`/chudthor` – Skurrile, kantigere Gesichtsverformung\n"
    "`/deepfry` – Übertriebene Farben, JPEG-Artefakte und zufällige Sticker\n"
    "**Neue Gesichtseffekte:** `/fatmagic`, `/tinyface`, `/bigmouth`, `/googly`, `/eyeswap`\n"
    "**Ultrawide:** `/wide` – ganzes Bild auf dreifache Breite ziehen\n"
    "**Trippy:** `/zoom`, `/tunnel`, `/kaleidoscope`, `/swirl`, `/rgbghost`\n"
    "**Euler:** `/droste`, `/complexsquare`, `/complexexp`, `/logpolar`, `/inversion`\n"
    "**Anime:** `/sweat`, `/sparkle`, `/angry`\n"
    "`/random` – zufälliger Effekt; `/help` – diese Hilfe\n\n"
    "Bei jedem Effekt kannst du **bild** hochladen oder eine **url** angeben. "
    "Ohne beides wird das letzte Bild im Kanal verwendet, auch ein vorheriges Bot-Ergebnis. "
    "Alle erkannten Gesichter werden bearbeitet. GIFs: erstes Einzelbild.\n"
    "Weiterhin möglich: `@SirMagick blockface` oder `@SirMagick help`."
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
            @discord.app_commands.describe(bild="Bild hochladen; sonst letztes Bild im Kanal",
                                           url="Alternativ eine öffentliche Bild-URL")
            async def callback(interaction: discord.Interaction,
                               bild: discord.Attachment | None = None, url: str | None = None):
                LOGGER.info("Slash-Aufruf: /%s | Server-ID %s | Kanal-ID %s", effect,
                            interaction.guild_id, interaction.channel_id)
                if not self.allowed(interaction.guild, interaction.channel):
                    await interaction.response.send_message("Hier ist der Bot nicht freigegeben.", ephemeral=True)
                    return
                if bild and url:
                    await interaction.response.send_message("Bitte entweder ein Bild oder eine URL angeben.", ephemeral=True)
                    return
                await interaction.response.defer(thinking=True)
                content = f"<@{self.user.id}> {effect}" + (f" {url}" if url else "")
                await self.on_message(InteractionMessage(interaction, content, bild))
            return discord.app_commands.Command(name=effect, description=descriptions[effect], callback=callback)

        for effect in descriptions:
            self.tree.add_command(discord.app_commands.guild_only()(effect_command(effect)))

        @self.tree.command(name="help", description="Alle Bildeffekte und ihre Verwendung anzeigen")
        @discord.app_commands.guild_only()
        async def help_command(interaction: discord.Interaction):
            LOGGER.info("Slash-Aufruf: /help | Server-ID %s | Kanal-ID %s",
                        interaction.guild_id, interaction.channel_id)
            if not self.allowed(interaction.guild, interaction.channel):
                await interaction.response.send_message("Hier ist der Bot nicht freigegeben.", ephemeral=True)
                return
            await interaction.response.send_message(HELP, ephemeral=True)

    async def setup_hook(self):
        # Sync once at startup, never on reconnect. Failure is visible in the
        # console while existing mention commands remain usable.
        LOGGER.info("Bot-Code: %s | Python: %s", Path(__file__).resolve(), sys.executable)
        await self.sync_commands()
        self.config.work.mkdir(parents=True, exist_ok=True)
        self.downloads = create_download_session(self.config.download_timeout)
        self.consumer = asyncio.create_task(self.consume())

    async def sync_commands(self):
        LOGGER.info("Registriere %d Slash-Befehle bei Discord (Application-ID: %s) …",
                    len(self.tree.get_commands()), self.application_id)
        try:
            async with asyncio.timeout(30):
                commands = await self.tree.sync()
            LOGGER.info("Discord bestätigt %d globale Slash-Befehle: %s", len(commands),
                        ", ".join("/" + command.name for command in commands))
        except discord.HTTPException as exc:
            LOGGER.warning("Slash-Registrierung fehlgeschlagen: HTTP %s, Discord-Code %s. "
                           "Bot-Einladung und applications.commands prüfen.", exc.status, exc.code)
        except TimeoutError:
            LOGGER.warning("Slash-Registrierung: keine Antwort innerhalb von 30 Sekunden.")

    async def sync_guild_commands(self, guild):
        if self.config.guild_ids and guild.id not in self.config.guild_ids:
            return
        async with self.guild_sync_lock:
            if guild.id in self.guild_sync_attempted:
                return
            self.guild_sync_attempted.add(guild.id)
            self.tree.copy_global_to(guild=guild)
            try:
                async with asyncio.timeout(30):
                    commands = await self.tree.sync(guild=guild)
                LOGGER.info("Discord bestätigt %d Slash-Befehle direkt auf Server %s (%s).",
                            len(commands), guild.name, guild.id)
            except discord.HTTPException as exc:
                LOGGER.warning("Server-Slash-Registrierung fehlgeschlagen auf %s: HTTP %s, Discord-Code %s. "
                               "Server-Installation mit bot und applications.commands prüfen.",
                               guild.id, exc.status, exc.code)
            except TimeoutError:
                LOGGER.warning("Server-Slash-Registrierung auf %s: Zeitlimit erreicht.", guild.id)

    async def slash_error(self, interaction, error):
        LOGGER.warning("Slash-Aufruf fehlgeschlagen: %s | Server-ID %s | Kanal-ID %s",
                       type(error).__name__, interaction.guild_id, interaction.channel_id)
        text = "Slash-Aufruf fehlgeschlagen. Bitte @sirmagick help verwenden und die Bot-Konsole prüfen."
        try:
            async with asyncio.timeout(self.config.upload_timeout):
                if interaction.response.is_done():
                    await interaction.followup.send(text, ephemeral=True)
                else:
                    await interaction.response.send_message(text, ephemeral=True)
        except (discord.HTTPException, TimeoutError):
            LOGGER.warning("Slash-Fehlermeldung konnte nicht gesendet werden.")

    async def on_guild_join(self, guild):
        await self.sync_guild_commands(guild)

    async def on_ready(self):
        LOGGER.info("Verbunden als %s (Bot-ID: %s), erreichbar auf %d Servern. "
                    "Hilfe im Kanal: @%s help", self.user, self.user.id, len(self.guilds), self.user.name)
        LOGGER.info("Serverfilter: %s | Kanalfilter: %s | Message-Content-Intent im Code: %s",
                    sorted(self.config.guild_ids) or "alle", sorted(self.config.channel_ids) or "alle",
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
            logging.warning("Statusnachricht konnte nicht gesendet werden.")

    async def on_message(self, message):
        cfg = self.config
        if message.author.bot or not message.guild or not self.user:
            return
        if not self.allowed(message.guild, message.channel):
            if message.content.lstrip().lower().startswith(("@sirmagick", f"<@{self.user.id}>", f"<@!{self.user.id}>")):
                LOGGER.warning("Befehl durch Filter ignoriert: Server-ID %s, Kanal-ID %s.",
                               message.guild.id, message.channel.id)
            return
        try:
            command = parse_command(message.content, self.user.id)
            if command is None:
                return
            LOGGER.info("Befehl erkannt: %s | Server-ID %s | Kanal-ID %s", command.effect,
                        message.guild.id, message.channel.id)
            if command.effect == "help":
                await self.reply(message, HELP)
                return
            now = monotonic()
            self.cooldowns = {key: expiry for key, expiry in self.cooldowns.items() if expiry > now}
            user = message.author.id
            if user in self.pending or user in self.cooldowns:
                raise ValueError("Bitte kurz warten, bevor du ein weiteres Bild beauftragst.")
            job = Job(message, command)
            try:
                self.jobs.put_nowait(job)
            except asyncio.QueueFull:
                raise ValueError("Warteschlange ist voll. Bitte später erneut versuchen.") from None
            self.pending.add(user)
            self.cooldowns[user] = now + cfg.cooldown
            try:
                job.status = await self.reply(message, "Bildauftrag angenommen.")
            finally:
                job.ready.set()
        except ValueError as exc:
            await self.reply(message, str(exc))
        except discord.HTTPException as exc:
            LOGGER.warning("Befehlsantwort fehlgeschlagen: HTTP %s, Discord-Code %s. "
                           "Send Messages und Kanalrechte prüfen.", exc.status, exc.code)
        except TimeoutError:
            LOGGER.warning("Zeitlimit beim Senden der Befehlsantwort erreicht.")

    async def consume(self):
        cfg = self.config
        while True:
            job = await self.jobs.get()
            directory = cfg.work / uuid4().hex
            try:
                await job.ready.wait()
                await self.status(job, "Bild wird verarbeitet …")
                directory.mkdir()
                async with asyncio.timeout(cfg.download_timeout):
                    url = job.command.url or await find_image(job.message, cfg.history_limit, cfg.max_download)
                    source = directory / "input"
                    await download_image(self.downloads, url, source, cfg.max_download, cfg.download_timeout)
                output = await self.worker.run({
                    "effect": job.command.effect, "source": str(source),
                    "destination": str(directory / "result"), "models": str(cfg.models),
                    "max_side": cfg.max_side, "max_people": cfg.max_people,
                    "max_output": min(cfg.max_output, job.message.guild.filesize_limit),
                }, cfg.process_timeout)
                attachment = discord.File(output, filename=output.name)
                try:
                    label = job.command.effect
                    if label == "random" and "-random-" in output.stem:
                        label = "random → " + output.stem.split("-random-", 1)[1]
                    await self.reply(job.message, label, file=attachment)
                finally:
                    attachment.close()
                await self.status(job, "Fertig.")
            except TimeoutError:
                await self.status(job, "Zeitlimit erreicht. Auftrag abgebrochen.")
            except ValueError as exc:
                await self.status(job, str(exc))
            except Exception:
                logging.warning("Bildauftrag fehlgeschlagen; Warteschlange läuft weiter.")
                await self.status(job, "Auftrag fehlgeschlagen. Bild, Bot-Rechte und Modelle prüfen.")
            finally:
                self.pending.discard(job.message.author.id)
                self.jobs.task_done()
                if directory.exists() and directory.resolve().parent == cfg.work.resolve():
                    try:
                        shutil.rmtree(directory)
                    except OSError:
                        logging.warning("Arbeitsdateien konnten nicht entfernt werden.")


def run_bot():
    from dotenv import load_dotenv
    from .bot_config import BotConfig
    load_dotenv(override=False)
    config = BotConfig.from_env()
    logging.basicConfig(level=logging.WARNING)
    MagickBot(config).run(config.token, log_handler=None)
