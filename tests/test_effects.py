import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from sirmagick.data import Detection, NoDetectionError
from sirmagick.effects import EFFECTS, FACE_EFFECTS, EULER, TRIPPY, ANIME, apply_effect, resolve_effect
from test_chudthor import synthetic_face


class EffectTests(unittest.TestCase):
    def test_image_modes_repeat_without_faces_and_preserve_source(self):
        pixels = np.random.default_rng(12).integers(0, 256, (49, 65, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        for name in sorted(EULER | TRIPPY | {"wide"}):
            with self.subTest(name=name):
                first = apply_effect(image, None, name)
                second = apply_effect(first, None, name)
                expected = (image.width*9, image.height) if name == "wide" else image.size
                self.assertEqual(second.size, expected)
                self.assertEqual(second.mode, "RGBA")
                self.assertFalse(np.array_equal(np.asarray(first), pixels))
                np.testing.assert_array_equal(np.asarray(image), pixels)

    def test_transparent_red_has_no_black_halos_in_image_maps(self):
        image = Image.new("RGBA", (65, 49), (0, 0, 0, 0))
        image.paste((255, 0, 0, 255), (15, 10, 50, 40))
        for name in sorted(EULER | TRIPPY):
            with self.subTest(name=name):
                pixels = np.asarray(apply_effect(image, None, name))
                visible = pixels[..., 3] > 10
                # RGB split intentionally shifts colors independently.
                if name != "rgbghost":
                    self.assertTrue(np.all(pixels[..., 0][visible] >= 254))
                self.assertTrue(np.all(pixels[..., 1] == 0))
                self.assertTrue(np.all(pixels[..., 2] == 0))

    def test_face_modes_require_real_matching_detection(self):
        image = Image.new("RGBA", (100, 100))
        empty = Detection(100, 100, 100, 100, [], [], 0)
        wrong_size = Detection(200, 200, 100, 100, [synthetic_face(50, 50)], [], 0)
        for name in FACE_EFFECTS:
            with self.subTest(name=name):
                with self.assertRaises(NoDetectionError):
                    apply_effect(image, empty, name)
                with self.assertRaises(ValueError):
                    apply_effect(image, wrong_size, name)

    def test_anime_anchors_on_all_faces_and_keeps_alpha(self):
        pixels = np.random.default_rng(6).integers(0, 256, (160, 200, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        detection = Detection(200, 160, 200, 160,
                              [synthetic_face(50, 80), synthetic_face(150, 80)], [], 0)
        for name in ANIME:
            with self.subTest(name=name):
                output = np.asarray(apply_effect(image, detection, name))
                for x in (50, 150):
                    self.assertFalse(np.array_equal(output[40:110, x-25:x+25], pixels[40:110, x-25:x+25]))
                np.testing.assert_array_equal(output[..., 3], pixels[..., 3])
                np.testing.assert_array_equal(np.asarray(image), pixels)

    def test_random_resolves_once_and_cannot_select_itself(self):
        with patch("sirmagick.effects.secrets.choice", return_value="droste") as choice:
            self.assertEqual(resolve_effect("random"), "droste")
            self.assertNotIn("random", choice.call_args.args[0])
        self.assertIn("uwu", EFFECTS)
        self.assertIn("blush", EFFECTS)
        with self.assertRaises(ValueError):
            apply_effect(Image.new("RGB", (4, 4)), None, "random")

    def test_blush_keeps_background_and_feature_pixels_unchanged(self):
        pixels = np.random.default_rng(19).integers(30, 230, (160, 200, 4), dtype=np.uint8)
        face = synthetic_face(100, 80)
        detection = Detection(200, 160, 200, 160, [face], [], 0)
        image = Image.fromarray(pixels)
        first = apply_effect(image, detection, "blush")
        second = apply_effect(first, detection, "blush")
        for result in (np.asarray(first), np.asarray(second)):
            np.testing.assert_array_equal(result[:60], pixels[:60])
            np.testing.assert_array_equal(result[101:], pixels[101:])
            np.testing.assert_array_equal(result[:, :85], pixels[:, :85])
            np.testing.assert_array_equal(result[:, 116:], pixels[:, 116:])
            for index in (33, 263, 1, 61, 291):
                x, y = round(face[index].x), round(face[index].y)
                np.testing.assert_array_equal(result[y, x], pixels[y, x])

    def test_cute_effects_handle_rotated_faces_at_image_edges(self):
        from sirmagick.data import Point
        pixels = np.random.default_rng(22).integers(20, 240, (50, 50, 4), dtype=np.uint8)
        face = synthetic_face(6, 8)
        angle = .55
        rotated = [Point(6+(p.x-6)*np.cos(angle)-(p.y-8)*np.sin(angle),
                         8+(p.x-6)*np.sin(angle)+(p.y-8)*np.cos(angle)) for p in face]
        detection = Detection(50, 50, 50, 50, [rotated], [], 0)
        image = Image.fromarray(pixels)
        for mode in ("uwu", "blush"):
            with self.subTest(mode=mode):
                result = np.asarray(apply_effect(image, detection, mode))
                np.testing.assert_array_equal(result[..., 3], pixels[..., 3])
                self.assertFalse(np.array_equal(result, pixels))
                np.testing.assert_array_equal(result[35:, 35:], pixels[35:, 35:])

    def test_ultrawide_rejects_output_above_pixel_limit_before_resize(self):
        with patch("sirmagick.images.MAX_PIXELS", 100):
            with self.assertRaises(ValueError):
                apply_effect(Image.new("RGB", (10, 10)), None, "wide")
