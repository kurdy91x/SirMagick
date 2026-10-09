import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from sirmagick.data import Detection
from sirmagick.effects import apply_effect
from test_chudthor import synthetic_face


class FaceFantasyTests(unittest.TestCase):
    def test_vortex_bounds_render_maps_and_restores_original_size_and_alpha(self):
        import cv2
        from sirmagick import vortexcolumns
        pixels = np.random.default_rng(7).integers(0,256,(230,320,4),dtype=np.uint8)
        image = Image.fromarray(pixels)
        detection = Detection(320,230,320,230,[synthetic_face(160,100)],[],0)
        with patch.object(vortexcolumns,'MAX_RENDER_SIDE',128), patch.object(vortexcolumns,'STRIPE_ROWS',24):
            with patch.object(vortexcolumns.cv2,'remap',wraps=cv2.remap) as remap:
                result = np.asarray(apply_effect(image,detection,'mouthvortex'))
                self.assertGreater(remap.call_count,3)
                for call in remap.call_args_list:
                    self.assertLessEqual(call.args[1].shape[0],24)
                    self.assertLessEqual(call.args[1].shape[1],128)
        self.assertEqual(result.shape,pixels.shape)
        np.testing.assert_array_equal(result[...,3],pixels[...,3])
        np.testing.assert_array_equal(np.asarray(image),pixels)

    def test_both_heads_are_decorated_without_changing_alpha_or_source(self):
        pixels = np.full((180, 240, 4), (75, 110, 130, 175), np.uint8)
        image = Image.fromarray(pixels)
        detection = Detection(240, 180, 240, 180, [synthetic_face(60, 90), synthetic_face(180, 90)], [], 0)
        for mode in ("halo", "devilhorns"):
            with self.subTest(mode=mode):
                output = np.asarray(apply_effect(image, detection, mode))
                for x in (60, 180):
                    self.assertFalse(np.array_equal(output[30:90, x-45:x+45], pixels[30:90, x-45:x+45]))
                np.testing.assert_array_equal(output[..., 3], pixels[..., 3])
                np.testing.assert_array_equal(output[120:], pixels[120:])
                np.testing.assert_array_equal(np.asarray(image), pixels)

    def test_vortex_uses_each_face_as_texture_and_keeps_size_alpha(self):
        pixels = np.full((180, 240, 4), (0, 0, 0, 200), np.uint8)
        pixels[60:115, 35:85, :3] = (250, 15, 15)
        pixels[60:115, 155:205, :3] = (15, 15, 250)
        image = Image.fromarray(pixels)
        detection = Detection(240, 180, 240, 180, [synthetic_face(60, 90), synthetic_face(180, 90)], [], 0)
        for mode in ("vortexcolumns", "eyevortex", "mouthvortex"):
            with self.subTest(mode=mode):
                output = np.asarray(apply_effect(image, detection, mode))
                self.assertEqual(output.shape, pixels.shape)
                np.testing.assert_array_equal(output[..., 3], pixels[..., 3])
                np.testing.assert_array_equal(np.asarray(image), pixels)
                self.assertTrue(np.any(output[..., 0].astype(int)-output[..., 2] > 70))
                self.assertTrue(np.any(output[..., 2].astype(int)-output[..., 0] > 70))

    def test_eye_and_mouth_textures_are_distinct_from_each_other_and_whole_face(self):
        pixels = np.random.default_rng(13).integers(0, 256, (180, 240, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        detection = Detection(240, 180, 240, 180, [synthetic_face(120, 90)], [], 0)
        outputs = [np.asarray(apply_effect(image, detection, mode))
                   for mode in ("vortexcolumns", "eyevortex", "mouthvortex")]
        for a, b in ((0, 1), (0, 2), (1, 2)):
            self.assertFalse(np.array_equal(outputs[a], outputs[b]))
