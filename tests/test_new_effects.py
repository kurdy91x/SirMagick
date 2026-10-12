import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import numpy as np
from PIL import Image

from sirmagick.bot_commands import parse_command
from sirmagick.data import Detection,Point
from sirmagick.effects import TRANSFORMERS,FACE_MASKS,MEMES,STYLIZED,apply_effect,resolve_effect
from sirmagick.effect_options import achievement_parts
from sirmagick.meme_frames import _post_ids
from test_chudthor import synthetic_face


class NewEffectTests(unittest.TestCase):
    def test_hornijail_replaces_only_window_panes(self):
        from pathlib import Path
        import sirmagick.meme_frames as memes
        with Image.open(Path(memes.__file__).parent/'assets'/'horni.jail.jpg') as asset:
            template = np.array(asset.convert('RGBA'))
        result = np.array(apply_effect(Image.new('RGBA',(70,90),(255,0,128,255)),None,'hornijail'))
        self.assertEqual(result.shape,template.shape)
        for x,y in ((240,240),(380,240),(520,220)):
            np.testing.assert_array_equal(result[y,x],[255,0,128,255])
        np.testing.assert_array_equal(result[450:],template[450:])

    def test_surveillance_tracks_multiple_faces_without_modifying_input(self):
        image = Image.new('RGBA',(500,350),(90,105,115,170))
        detection = Detection(500,350,500,350,[synthetic_face(140,160),synthetic_face(360,160)],[],0)
        original = np.array(image)
        result = np.array(apply_effect(image,detection,'surveillance'))
        red = (result[...,0]>200)&(result[...,1]<100)
        green = (result[...,1]>200)&(result[...,0]<150)
        self.assertGreater(int(red[:,:250].sum()),50)
        self.assertGreater(int(green[:,250:].sum()),50)
        np.testing.assert_array_equal(result[...,3],original[...,3])
        np.testing.assert_array_equal(np.array(image),original)

    def test_same_size_effects_preserve_alpha_and_input(self):
        pixels = np.random.default_rng(5).integers(0,256,(100,140,4),dtype=np.uint8)
        image = Image.fromarray(pixels)
        detection = Detection(140,100,140,100,[synthetic_face(45,50),synthetic_face(100,50)],[],0)
        for mode in sorted(TRANSFORMERS|FACE_MASKS|STYLIZED|(MEMES-{'achievement','chanpost','hornijail'})):
            with self.subTest(mode=mode):
                output = apply_effect(image,detection,mode)
                self.assertEqual(output.size,image.size)
                np.testing.assert_array_equal(np.asarray(output)[...,3],pixels[...,3])
                np.testing.assert_array_equal(np.asarray(image),pixels)

    def test_image_only_modes_handle_tiny_inputs(self):
        for size in ((1,1),(1,8),(8,1)):
            for mode in STYLIZED|(MEMES-{'achievement','chanpost','hornijail'}):
                with self.subTest(size=size,mode=mode):
                    image = Image.new('RGBA',size,(50,100,150,100))
                    self.assertEqual(apply_effect(image,None,mode).size,size)

    def test_censorbar_covers_both_faces_and_leaves_distant_pixels_alone(self):
        image = Image.new('RGBA',(200,130),(180,150,130,190))
        detection = Detection(200,130,200,130,[synthetic_face(50,60),synthetic_face(150,60)],[],0)
        pixels = np.asarray(apply_effect(image,detection,'censorbar'))
        for x in (50,150):
            self.assertTrue((pixels[54,x,:3]==0).all())
        np.testing.assert_array_equal(pixels[0],np.asarray(image)[0])

    def test_fatmagic_changes_body_when_pose_is_present(self):
        yy,xx = np.mgrid[:180,:180]
        image = Image.fromarray(np.uint8(np.stack((xx,yy,(xx+yy)/2,np.full_like(xx,255)),-1)))
        face = synthetic_face(90,40)
        pose = [Point(90,100,0) for _ in range(33)]
        for index,(x,y) in {11:(55,70),12:(125,70),23:(65,140),24:(115,140)}.items():
            pose[index] = Point(x,y,1)
        no_body = Detection(180,180,180,180,[face],[],0)
        body = Detection(180,180,180,180,[face],[pose],0)
        a = np.asarray(apply_effect(image,no_body,'fatmagic'))
        b = np.asarray(apply_effect(image,body,'fatmagic'))
        self.assertGreater(float(np.abs(a[90:150].astype(float)-b[90:150]).mean()),1)

    def test_achievement_text_and_post_ids(self):
        self.assertEqual(achievement_parts('TouchGrass Finally went outside.'),['TouchGrass','Finally went outside.'])
        command = parse_command('@sirmagick achievement TouchGrass Finally went outside. https://example.org/image.png',42)
        self.assertEqual(command.text,'TouchGrass Finally went outside.')
        self.assertEqual(command.url,'https://example.org/image.png')
        for value in (None,'','OneWord','a '*205):
            with self.assertRaises(ValueError):
                achievement_parts(value)
        ids = _post_ids(np.random.default_rng(4),200)
        self.assertEqual(len(set(ids)),200)
        self.assertTrue(all(value[-1]==value[-2] for value in ids))
        image = Image.new('RGBA',(90,140),(20,100,180,255))
        self.assertEqual(apply_effect(image,None,'achievement',text='Title Some description').size,(1200,650))
        screenshot = apply_effect(image,None,'chanpost')
        self.assertEqual(screenshot.size,(1200,820))
        np.testing.assert_array_equal(np.asarray(screenshot)[60,30,:3],[20,100,180])

    def test_body_deformation_leaves_pixels_above_shoulders_unchanged(self):
        from sirmagick.face_transformers import warp_region
        pixels = np.random.default_rng(3).integers(0,256,(150,130,4),dtype=np.uint8)
        original = pixels.copy()
        warp_region(pixels,[(35,60),(95,60),(45,120),(85,120)],1.7,.78,vertical_limits=(60,120))
        np.testing.assert_array_equal(pixels[:60],original[:60])
        self.assertFalse(np.array_equal(pixels[70:120],original[70:120]))

    def test_random_excludes_effect_requiring_text(self):
        with patch('sirmagick.effects.secrets.choice',return_value='hodl') as choose:
            self.assertEqual(resolve_effect('random'),'hodl')
            self.assertNotIn('achievement',choose.call_args.args[0])


class AchievementSlashTests(unittest.IsolatedAsyncioTestCase):
    async def test_achievement_worker_receives_required_text(self):
        from test_core import fixture_directory
        from sirmagick.worker import ProcessWorker
        worker = ProcessWorker()
        with fixture_directory() as root:
            source = root/'input.png'
            Image.new('RGB',(40,60),'teal').save(source)
            request = dict(effect='achievement',text='TouchGrass Finally went outside.',source=str(source),
                           destination=str(root/'result'),models='models',max_side=1024,max_people=20,max_output=2*1024*1024)
            try:
                output = await worker.run(request,15)
                with Image.open(output) as result:
                    self.assertEqual(result.size,(1200,650))
            finally:
                await worker.close()

    async def test_required_text_reaches_shared_queue(self):
        from sirmagick.bot_config import BotConfig
        from sirmagick.discord_bot import MagickBot,HELP
        bot = MagickBot(BotConfig(token='unused'))
        bot._connection.user = SimpleNamespace(id=42)
        bot.on_message = AsyncMock()
        interaction = SimpleNamespace(guild_id=1,channel_id=2,id=123,
            user=SimpleNamespace(id=5,bot=False),guild=SimpleNamespace(id=1),channel=SimpleNamespace(id=2),
            response=SimpleNamespace(defer=AsyncMock(),send_message=AsyncMock()))
        try:
            command = bot.tree.get_command('sm_achievement')
            schema = command.to_dict(bot.tree)
            self.assertEqual(schema['options'][0]['name'],'text')
            self.assertTrue(schema['options'][0]['required'])
            self.assertLess(len(HELP),2000)
            await command.callback(interaction,text='TouchGrass Finally went outside.')
            message = bot.on_message.await_args.args[0]
            self.assertEqual(parse_command(message.content,42).text,'TouchGrass Finally went outside.')
            bot.on_message.reset_mock()
            await command.callback(interaction,text='Incomplete')
            bot.on_message.assert_not_awaited()
        finally:
            await bot.close()
