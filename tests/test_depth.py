import unittest

import numpy as np
from PIL import Image

from sirmagick.effects import DEPTH, apply_effect


class DepthTests(unittest.TestCase):
    def test_repeat_keeps_dimensions_alpha_and_source_without_faces(self):
        pixels = np.random.default_rng(41).integers(0, 256, (67, 89, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        for mode in DEPTH:
            with self.subTest(mode=mode):
                first = apply_effect(image, None, mode)
                second = apply_effect(first, None, mode)
                self.assertEqual(second.size, image.size)
                np.testing.assert_array_equal(np.asarray(second)[..., 3], pixels[..., 3])
                np.testing.assert_array_equal(np.asarray(image), pixels)
                self.assertFalse(np.array_equal(np.asarray(first), pixels))

    def test_hidden_colors_do_not_affect_visible_results(self):
        a = np.full((35, 45, 4), (255, 0, 0, 0), np.uint8)
        a[10:25, 12:32] = (160, 180, 200, 255)
        b = a.copy()
        b[b[..., 3] == 0, :3] = (0, 255, 255)
        visible = a[..., 3] > 0
        for mode in DEPTH:
            with self.subTest(mode=mode):
                first = np.asarray(apply_effect(Image.fromarray(a), None, mode))
                second = np.asarray(apply_effect(Image.fromarray(b), None, mode))
                np.testing.assert_array_equal(first[visible], second[visible])

    def test_tiny_images_work(self):
        for size in ((1, 1), (1, 5), (5, 1)):
            for mode in DEPTH:
                with self.subTest(size=size, mode=mode):
                    self.assertEqual(apply_effect(Image.new("RGBA", size), None, mode).size, size)
