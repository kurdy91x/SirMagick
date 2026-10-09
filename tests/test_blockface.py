import unittest
import numpy as np
from PIL import Image

from sirmagick.blockface import apply_blockface, _face_map, _source_radius, FACE_SCALE, INNER_RADIUS
from sirmagick.data import Detection, NoDetectionError
from test_chudthor import synthetic_face


class BlockfaceTests(unittest.TestCase):
    def test_uniform_inner_scaling_fixed_border_and_no_folding(self):
        radius = np.linspace(0, INNER_RADIUS*FACE_SCALE, 100)
        np.testing.assert_allclose(_source_radius(radius), radius/FACE_SCALE)
        self.assertAlmostEqual(float(_source_radius(np.array(1.0))), 1.0)
        r = np.linspace(0, 1.5, 10000)
        self.assertTrue(np.all(np.diff(_source_radius(r)) > 0))
        self.assertAlmostEqual(float(_source_radius(np.array(INNER_RADIUS*FACE_SCALE))), INNER_RADIUS)

    def test_inner_mapping_keeps_all_proportions(self):
        bounds, sx, sy, active, radius = _face_map(synthetic_face(60, 60), 120, 120)
        x0, y0, x1, y1 = bounds
        xx, yy = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
        inner = radius < INNER_RADIUS*FACE_SCALE
        self.assertTrue(inner.any())
        for values, coordinates in ((sx, xx), (sy, yy)):
            offsets = (values-coordinates/FACE_SCALE)[inner]
            np.testing.assert_allclose(offsets, np.full_like(offsets, offsets[0]), atol=1e-5)

    def test_every_pixel_outside_faces_is_identical(self):
        pixels = np.random.default_rng(5).integers(0, 256, (160, 200, 4), dtype=np.uint8)
        image = Image.fromarray(pixels)
        faces = [synthetic_face(50, 80), synthetic_face(150, 80)]
        result = np.array(apply_blockface(image, Detection(200, 160, 200, 160, faces, [], 0)))
        active_all = np.zeros((160, 200), bool)
        for face in faces:
            (x0, y0, x1, y1), _, _, active, _ = _face_map(face, 200, 160)
            active_all[y0:y1, x0:x1] |= active
            self.assertFalse(np.array_equal(result[y0:y1, x0:x1][active], pixels[y0:y1, x0:x1][active]))
        np.testing.assert_array_equal(result[~active_all], pixels[~active_all])
        np.testing.assert_array_equal(np.array(image), pixels)
        self.assertEqual(result.shape, pixels.shape)

    def test_missing_face_and_wrong_dimensions(self):
        image = Image.new("RGBA", (100, 100))
        with self.assertRaises(NoDetectionError):
            apply_blockface(image, Detection(100, 100, 100, 100, [], [], 0))
        with self.assertRaises(ValueError):
            apply_blockface(image, Detection(200, 200, 100, 100, [synthetic_face(50, 50)], [], 0))


if __name__ == "__main__":
    unittest.main()
