import unittest

import numpy as np
from PIL import Image

from sirmagick.effects import TYPOGRAPHY, apply_effect


class TypographyTests(unittest.TestCase):
    def test_modes_repeat_without_faces_and_preserve_dimensions_alpha_source(self):
        pixels = np.random.default_rng(16).integers(0, 256, (81, 105, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        outputs = []
        for mode in TYPOGRAPHY:
            first = apply_effect(image, None, mode)
            second = apply_effect(first, None, mode)
            self.assertEqual(second.size, image.size)
            np.testing.assert_array_equal(np.asarray(second)[..., 3], pixels[..., 3])
            np.testing.assert_array_equal(np.asarray(image), pixels)
            outputs.append(np.asarray(first))
        self.assertFalse(np.array_equal(*outputs))

    def test_tiny_images_and_hidden_colors(self):
        for size in ((1, 1), (1, 5), (5, 1)):
            for mode in TYPOGRAPHY:
                self.assertEqual(apply_effect(Image.new("RGBA", size), None, mode).size, size)
        a = np.full((80, 100, 4), (255, 0, 0, 0), np.uint8)
        a[20:60, 30:70] = (140, 180, 240, 255)
        b = a.copy()
        b[b[..., 3] == 0, :3] = (0, 255, 0)
        for mode in TYPOGRAPHY:
            first = np.asarray(apply_effect(Image.fromarray(a), None, mode))
            second = np.asarray(apply_effect(Image.fromarray(b), None, mode))
            np.testing.assert_array_equal(first, second)
