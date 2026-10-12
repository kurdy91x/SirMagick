import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unittest.mock import AsyncMock

from PIL import Image

from sirmagick.bot_commands import parse_command, find_image
from sirmagick.bot_config import BotConfig
from sirmagick.downloads import validate_url, download_image
from sirmagick.worker import ProcessWorker
from test_core import fixture_directory


class BotTests(unittest.IsolatedAsyncioTestCase):
    async def test_guild_duplicates_are_removed_once_and_global_commands_survive(self):
        from sirmagick.discord_bot import MagickBot
        from sirmagick.effects import EFFECTS
        bot = MagickBot(BotConfig(token="unused", guild_ids=frozenset({1})))
        bot.tree.sync = AsyncMock(return_value=[SimpleNamespace(name="sm_help")])
        guild = SimpleNamespace(id=1, name="test")
        import discord
        bot.tree.add_command(discord.app_commands.Command(name="help", description="Legacy help",
            callback=bot.tree.get_command("sm_help").callback), guild=guild)
        try:
            await bot.sync_commands()
            bot.tree.sync.reset_mock()
            bot.tree.sync.return_value = []
            with self.assertLogs("sirmagick.discord_bot", level="INFO"):
                await asyncio.gather(bot.sync_guild_commands(guild), bot.sync_guild_commands(guild))
            bot.tree.sync.assert_awaited_once_with(guild=guild)
            self.assertEqual(bot.tree.get_commands(guild=guild), [])
            self.assertEqual({cmd.name for cmd in bot.tree.get_commands()}, {"sm_"+name for name in EFFECTS | {"help"}})
            await bot.sync_guild_commands(SimpleNamespace(id=2, name="excluded"))
            self.assertEqual(bot.tree.sync.await_count, 2)
        finally:
            await bot.close()

    async def test_slash_errors_respond_before_and_after_defer(self):
        from sirmagick.discord_bot import MagickBot
        bot = MagickBot(BotConfig(token="unused"))
        interaction = SimpleNamespace(guild_id=1, channel_id=2,
            response=SimpleNamespace(is_done=lambda: False, send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()))
        try:
            with self.assertLogs("sirmagick.discord_bot", level="WARNING"):
                await bot.slash_error(interaction, ValueError("not logged"))
            interaction.response.send_message.assert_awaited_once()
            interaction.response.is_done = lambda: True
            with self.assertLogs("sirmagick.discord_bot", level="WARNING"):
                await bot.slash_error(interaction, ValueError("not logged"))
            interaction.followup.send.assert_awaited_once()
        finally:
            await bot.close()

    async def test_command_sync_reports_discord_confirmation_and_errors(self):
        import discord
        from sirmagick.discord_bot import MagickBot
        bot = MagickBot(BotConfig(token="unused"))
        bot.tree.sync = AsyncMock(return_value=[SimpleNamespace(name="sm_help")])
        try:
            with self.assertLogs("sirmagick.discord_bot", level="INFO") as logs:
                await bot.sync_commands()
            self.assertTrue(any("confirmed 1" in line and "/sm_help" in line for line in logs.output))
            bot.tree.sync.side_effect = discord.HTTPException(
                SimpleNamespace(status=403, reason="Forbidden"), {"code": 50001, "message": "Missing Access"})
            with self.assertLogs("sirmagick.discord_bot", level="WARNING") as logs:
                await bot.sync_commands()
            self.assertIn("HTTP 403, Discord code 50001", logs.output[0])
            before = bot.tree.sync.await_count
            await bot.sync_guild_commands(SimpleNamespace(id=1,name='test'))
            self.assertEqual(bot.tree.sync.await_count,before)
        finally:
            await bot.close()

    async def test_slash_commands_share_queue_and_support_upload(self):
        from sirmagick.discord_bot import MagickBot
        bot = MagickBot(BotConfig(token="unused"))
        bot._connection.user = SimpleNamespace(id=42)
        interaction = SimpleNamespace(
            id=123, guild_id=1, channel_id=2, user=SimpleNamespace(id=7, bot=False),
            guild=SimpleNamespace(id=1), channel=SimpleNamespace(id=2, send=AsyncMock()),
            response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()))
        attachment = SimpleNamespace(filename="test.png")
        try:
            commands = {command.name: command for command in bot.tree.get_commands()}
            from sirmagick.effects import EFFECTS
            self.assertEqual(set(commands), {"sm_"+name for name in EFFECTS | {"help"}})
            schema = commands["sm_blockface"].to_dict(bot.tree)
            self.assertEqual([option["name"] for option in schema["options"]], ["image", "url"])
            await commands["sm_blockface"].callback(interaction, image=attachment)
            interaction.response.defer.assert_awaited_once_with(thinking=True)
            job = bot.jobs.get_nowait()
            self.assertEqual(job.command.effect, "blockface")
            self.assertEqual(job.message.attachments, [attachment])
            self.assertTrue(job.ready.is_set())
            bot.jobs.task_done()
            await commands["sm_deepfry"].callback(interaction)
            self.assertTrue(bot.jobs.empty())
            self.assertIn("wait", interaction.followup.send.call_args.args[0])
            await job.message.reply("result")
            interaction.channel.send.assert_awaited_once()
        finally:
            await bot.close()

    async def test_slash_help_and_invalid_inputs_do_not_queue(self):
        from sirmagick.discord_bot import MagickBot
        bot = MagickBot(BotConfig(token="unused", channel_ids=frozenset({2})))
        interaction = SimpleNamespace(guild_id=1, channel_id=2, guild=SimpleNamespace(id=1), channel=SimpleNamespace(id=2),
            response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()))
        try:
            await bot.tree.get_command("sm_help").callback(interaction)
            self.assertIn("/sm_blockface", interaction.response.send_message.call_args.args[0])
            self.assertTrue(interaction.response.send_message.call_args.kwargs["ephemeral"])
            await bot.tree.get_command("sm_deepfry").callback(interaction, image=object(), url="https://example.com/a")
            interaction.response.defer.assert_not_awaited()
            interaction.channel.id = 3
            await bot.tree.get_command("sm_deepfry").callback(interaction)
            self.assertIn("not enabled", interaction.response.send_message.call_args.args[0])
            self.assertTrue(bot.jobs.empty())
        finally:
            await bot.close()

    async def test_queue_continues_after_failure_and_cleans_files(self):
        from sirmagick.discord_bot import MagickBot, Job
        from sirmagick.bot_commands import Command
        with fixture_directory() as root:
            bot = MagickBot(BotConfig(token="unused", work=root))
            bot.status = AsyncMock()
            bot.reply = AsyncMock()
            message = SimpleNamespace(author=SimpleNamespace(id=1), guild=SimpleNamespace(filesize_limit=100000))
            calls = []
            async def process(request, timeout):
                calls.append(request["effect"])
                if len(calls) == 1:
                    raise ValueError("No face detected.")
                output = Path(request["destination"]).with_suffix(".png")
                Image.new("RGB", (16, 16)).save(output)
                return output
            async def download(session, url, destination, *args):
                destination.write_bytes(b"placeholder")
            bot.worker.run = process
            for effect in ("blockface", "deepfry"):
                job = Job(message, Command(effect, "https://example.com/a.png"))
                job.ready.set()
                bot.jobs.put_nowait(job)
            with patch("sirmagick.discord_bot.download_image", download):
                task = asyncio.create_task(bot.consume())
                await asyncio.wait_for(bot.jobs.join(), 5)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertEqual(calls, ["blockface", "deepfry"])
            self.assertEqual(bot.reply.await_count, 1)
            self.assertEqual(list(root.iterdir()), [])
            await bot.close()

    async def test_permission_failures_name_the_stage_and_do_not_block_queue(self):
        import discord
        from sirmagick.discord_bot import MagickBot, Job
        from sirmagick.bot_commands import Command
        for stage in ('image lookup','upload'):
            with self.subTest(stage=stage), fixture_directory() as root:
                bot = MagickBot(BotConfig(token='unused',work=root))
                bot.status = AsyncMock()
                forbidden = discord.Forbidden(SimpleNamespace(status=403,reason='Forbidden'),
                                              {'message':'Missing Permissions','code':50013})
                bot.reply = AsyncMock(side_effect=[forbidden,None] if stage=='upload' else None)
                message = SimpleNamespace(author=SimpleNamespace(id=1),
                                          guild=SimpleNamespace(id=10,filesize_limit=100000),
                                          channel=SimpleNamespace(id=20))
                async def process(request,timeout):
                    output = Path(request['destination']).with_suffix('.png')
                    Image.new('RGB',(16,16)).save(output)
                    return output
                async def download(session,url,destination,*args):
                    destination.write_bytes(b'placeholder')
                bot.worker.run = process
                for _ in range(2):
                    job = Job(message,Command('deepfry'))
                    job.ready.set()
                    bot.jobs.put_nowait(job)
                lookup = AsyncMock(side_effect=[forbidden,'https://example.com/image.png']
                                   if stage=='image lookup' else None,
                                   return_value='https://example.com/image.png')
                with patch('sirmagick.discord_bot.find_image',lookup), patch('sirmagick.discord_bot.download_image',download):
                    with self.assertLogs('sirmagick.discord_bot',level='WARNING') as logs:
                        task = asyncio.create_task(bot.consume())
                        await asyncio.wait_for(bot.jobs.join(),5)
                        task.cancel()
                        with self.assertRaises(asyncio.CancelledError):
                            await task
                self.assertIn('HTTP=403 Discord code=50013',' '.join(logs.output))
                statuses = [call.args[1] for call in bot.status.await_args_list]
                permission = 'Read Message History' if stage=='image lookup' else 'Attach Files'
                self.assertTrue(any(permission in text for text in statuses))
                self.assertIn('Done.',statuses)
                self.assertEqual(list(root.iterdir()),[])
                await bot.close()

    def test_commands(self):
        self.assertEqual(parse_command("@sirmagick help", 42).effect, "help")
        self.assertEqual(parse_command("@SirMagick blockface", 42).effect, "blockface")
        self.assertIsNone(parse_command("@sirmagickelse help", 42))
        self.assertIsNone(parse_command("hello <@42> deepfry", 42))
        self.assertEqual(parse_command("<@!42> BLOCKFACE", 42).effect, "blockface")
        self.assertEqual(parse_command("<@42>", 42).effect, "help")
        with self.assertRaises(ValueError):
            parse_command("<@42> nope", 42)

    def test_configuration_hides_token_and_validates(self):
        with patch.dict(os.environ, {"DISCORD_TOKEN": "secret", "QUEUE_SIZE": "2"}, clear=True):
            self.assertNotIn("secret", repr(BotConfig.from_env()))
            self.assertEqual(BotConfig.from_env().queue_size, 2)
            os.environ["QUEUE_SIZE"] = "0"
            with self.assertRaises(ValueError):
                BotConfig.from_env()

    def test_internal_urls_blocked(self):
        for url in ("file:///etc/passwd", "http://127.0.0.1/a", "http://[::1]/a",
                    "http://192.168.1.2/a", "http://localhost/a", "https://a:123/a",
                    "https://user:pass@example.com/a"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)
        validate_url("https://cdn.discordapp.com/a.png?signature=value")

    async def test_history_accepts_bot_results(self):
        async def history(**kwargs):
            yield SimpleNamespace(attachments=[SimpleNamespace(content_type="image/png", filename="x.png",
                   size=100, url="https://example.com/x.png")], embeds=[], content="", author=SimpleNamespace(bot=True))
        message = SimpleNamespace(attachments=[], embeds=[], content="<@42> deepfry",
                                  channel=SimpleNamespace(history=history))
        self.assertEqual(await find_image(message, 50, 1024), "https://example.com/x.png")

    async def test_redirect_cannot_access_internal_server(self):
        class Response:
            status = 302
            headers = {"Location": "http://127.0.0.1/private"}
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        calls = []
        def get(url, **kwargs):
            calls.append(url)
            return Response()
        with fixture_directory() as root:
            with self.assertRaises(ValueError):
                await download_image(SimpleNamespace(get=get), "https://example.com/a", root / "input", 1024, 2)
            self.assertEqual(len(calls), 1)
            self.assertFalse((root / "input").exists())

    async def test_real_worker_reuses_process_and_recovers_after_timeout(self):
        worker = ProcessWorker()
        with fixture_directory() as root:
            source = root / "input.png"
            Image.new("RGB", (64, 64), "red").save(source)
            request = dict(effect="deepfry", source=str(source), destination=str(root / "output"),
                           models="models", max_side=1024, max_people=20, max_output=1024*1024)
            try:
                output = await worker.run(request, 15)
                self.assertTrue(output.exists())
                pid = worker.process.pid
                await worker.run(request, 15)
                self.assertEqual(worker.process.pid, pid)
                with self.assertRaises(TimeoutError):
                    await worker.run(request, 0.000001)
                self.assertIsNone(worker.process)
                self.assertTrue((await worker.run(request, 15)).exists())
                self.assertNotEqual(worker.process.pid, pid)
            finally:
                await worker.close()
