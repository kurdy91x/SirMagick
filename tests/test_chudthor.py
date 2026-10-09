import unittest

import numpy as np
from PIL import Image

from sirmagick.chudthor import apply_chudthor, bilinear_rgba, radial_source, OVAL
from sirmagick.data import Detection, NoDetectionError, Point


def synthetic_face(cx, cy):
    face = [Point(cx, cy) for _ in range(478)]
    for index, angle in zip(OVAL, np.linspace(-np.pi/2, 3*np.pi/2, len(OVAL), endpoint=False)):
        face[index] = Point(cx+15*np.cos(angle), cy+20*np.sin(angle))
    for indices, x, y in (((33, 133, 159, 145), cx-6, cy-5),
                           ((263, 362, 386, 374), cx+6, cy-5),
                           ((61, 291, 0, 17, 13, 14), cx, cy+9),
                           ((98, 327, 1, 168, 2), cx, cy+2)):
        for i, index in enumerate(indices):
            face[index] = Point(x+(i%2)*3-1.5, y+(i//2)-1)
    return face


class ChudthorTests(unittest.TestCase):
    def test_warps_do_not_fold_or_cross_outer_boundary(self):
        radius = np.linspace(0, 3, 10000)
        for boundary, outer in ((0.48, 1.8), (1.38, 2.3), (1.55, 2.3)):
            mapped = radial_source(radius, boundary, outer)
            self.assertTrue(np.all(np.diff(mapped) >= 0))
            np.testing.assert_allclose(mapped[radius >= outer], radius[radius >= outer])

    def test_alpha_interpolation_does_not_add_black_edges(self):
        pixels = np.array([[[255, 0, 0, 255], [0, 0, 0, 0]]], dtype=np.uint8)
        sampled = bilinear_rgba(pixels, np.array([[0.5]]), np.array([[0.0]]))
        np.testing.assert_array_equal(sampled[0, 0], [255, 0, 0, 128])

    def test_all_faces_change_and_original_is_preserved(self):
        pixels = np.random.default_rng(7).integers(0, 256, (160, 200, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        detection = Detection(200, 160, 200, 160,
                              [synthetic_face(50, 80), synthetic_face(150, 80)], [], 0)
        result = np.array(apply_chudthor(image, detection))
        self.assertEqual(result.shape, pixels.shape)
        np.testing.assert_array_equal(np.array(image), pixels)
        np.testing.assert_array_equal(result[:10], pixels[:10])
        self.assertFalse(np.array_equal(result[60:100, 40:60], pixels[60:100, 40:60]))
        self.assertFalse(np.array_equal(result[60:100, 140:160], pixels[60:100, 140:160]))

    def test_missing_face_and_wrong_dimensions_rejected(self):
        image = Image.new("RGBA", (100, 100))
        with self.assertRaises(NoDetectionError):
            apply_chudthor(image, Detection(100, 100, 100, 100, [], [], 0))
        with self.assertRaises(ValueError):
            apply_chudthor(image, Detection(200, 200, 100, 100, [synthetic_face(50, 50)], [], 0))


if __name__ == "__main__":
    unittest.main()
