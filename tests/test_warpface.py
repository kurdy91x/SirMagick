import unittest

import numpy as np
from PIL import Image

from sirmagick.warpface import apply_warpface, _square_outer_cheeks, OVAL
from sirmagick.data import Detection, NoDetectionError
from test_chudthor import synthetic_face


class WarpfaceTests(unittest.TestCase):
    def test_missing_faces_and_dimensions_rejected(self):
        image = Image.new("RGBA", (100, 100))
        with self.assertRaises(NoDetectionError):
            apply_warpface(image, Detection(100, 100, 100, 100, [], [], 0))
        with self.assertRaises(ValueError):
            apply_warpface(image, Detection(200, 200, 100, 100, [synthetic_face(50, 50)], [], 0))

    def test_contour_edit_leaves_inner_face_pixels_unchanged(self):
        pixels = np.random.default_rng(2).integers(0, 256, (100, 100, 4), dtype=np.uint8)
        points = np.array([(p.x, p.y) for p in synthetic_face(50, 50)])
        mask = np.full((100, 100), 255, np.uint8)
        result, _ = _square_outer_cheeks(pixels, mask, points, 15, 20)
        np.testing.assert_array_equal(result[:, 45:55], pixels[:, 45:55])

    def test_compositing_preserves_input_dimensions_and_distant_background(self):
        pixels = np.random.default_rng(3).integers(0, 256, (160, 200, 4), dtype=np.uint8)
        pixels[..., 3] = 255
        image = Image.fromarray(pixels)
        detection = Detection(200, 160, 200, 160,
                              [synthetic_face(50, 80), synthetic_face(150, 80)], [], 0)
        output = np.array(apply_warpface(image, detection))
        self.assertEqual(output.shape, pixels.shape)
        np.testing.assert_array_equal(np.array(image), pixels)
        np.testing.assert_array_equal(output[:10], pixels[:10])
        self.assertFalse(np.array_equal(output[60:90, 40:60], pixels[60:90, 40:60]))
        self.assertFalse(np.array_equal(output[60:90, 140:160], pixels[60:90, 140:160]))


if __name__ == "__main__":
    unittest.main()
