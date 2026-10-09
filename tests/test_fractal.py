import unittest

import numpy as np
from PIL import Image

from sirmagick.effects import FRACTAL, apply_effect
from sirmagick.fractal import _field


class FractalTests(unittest.TestCase):
    def test_repeat_preserves_alpha_dimensions_and_source(self):
        pixels = np.random.default_rng(8).integers(0, 256, (53, 71, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        for mode in FRACTAL:
            with self.subTest(mode=mode):
                first = apply_effect(image, None, mode)
                second = apply_effect(first, None, mode)
                self.assertEqual(second.size, image.size)
                np.testing.assert_array_equal(np.asarray(second)[..., 3], pixels[..., 3])
                np.testing.assert_array_equal(np.asarray(image), pixels)
                self.assertFalse(np.array_equal(np.asarray(first), pixels))

    def test_poles_and_tiny_images_remain_finite(self):
        for mode in ("julia", "newton"):
            for size in ((1, 1), (1, 5), (5, 1), (65, 49)):
                with self.subTest(mode=mode, size=size):
                    for field in _field(*size, mode):
                        self.assertTrue(np.isfinite(field).all())
                    result = apply_effect(Image.new("RGBA", size, (200, 90, 20, 130)), None, mode)
                    self.assertEqual(result.size, size)
