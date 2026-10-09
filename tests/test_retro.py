import unittest

import numpy as np
from PIL import Image

from sirmagick.effects import apply_effect, RETRO


class RetroTests(unittest.TestCase):
    def test_retro_repeat_preserves_dimensions_alpha_and_source(self):
        pixels = np.random.default_rng(3).integers(0, 256, (51, 67, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        for mode in RETRO:
            with self.subTest(mode=mode):
                first = apply_effect(image, None, mode)
                second = apply_effect(first, None, mode)
                self.assertEqual(second.size, image.size)
                if mode != "crt":
                    np.testing.assert_array_equal(np.asarray(second)[..., 3], pixels[..., 3])
                self.assertFalse(np.array_equal(np.asarray(first), pixels))
                np.testing.assert_array_equal(np.asarray(image), pixels)

    def test_tiny_images_work(self):
        for size in ((1, 1), (1, 5), (5, 1)):
            for mode in RETRO | {"fisheye"}:
                with self.subTest(size=size, mode=mode):
                    self.assertEqual(apply_effect(Image.new("RGBA", size), None, mode).size, size)
