from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import sys
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from sirmagick.cli import main
from sirmagick.deepfry import apply_deepfry
from test_core import fixture_directory


class DeepfryTests(unittest.TestCase):
    def test_preserves_dimensions_alpha_and_original(self):
        pixels = np.random.default_rng(1).integers(0, 256, (72, 96, 4), dtype=np.uint8)
        original = Image.fromarray(pixels)
        output = np.array(apply_deepfry(original))
        self.assertEqual(output.shape, pixels.shape)
        np.testing.assert_array_equal(output[..., 3], pixels[..., 3])
        np.testing.assert_array_equal(np.array(original), pixels)
        self.assertFalse(np.array_equal(output[..., :3], pixels[..., :3]))

    def test_repeatable_but_second_application_changes_result(self):
        pixels = np.random.default_rng(3).integers(0, 256, (80, 100, 3), dtype=np.uint8)
        image = Image.fromarray(pixels)
        once = apply_deepfry(image, seed=42)
        np.testing.assert_array_equal(np.array(once), np.array(apply_deepfry(image, seed=42)))
        twice = apply_deepfry(once, seed=42)
        self.assertEqual(twice.size, image.size)
        self.assertFalse(np.array_equal(np.array(once), np.array(twice)))

    def test_small_and_grayscale_inputs_without_people(self):
        for mode in ("L", "RGB", "RGBA"):
            with self.subTest(mode=mode):
                result = apply_deepfry(Image.new(mode, (1, 1)))
                self.assertEqual(result.size, (1, 1))
                self.assertEqual(result.mode, "RGBA")

    def test_batch_needs_no_detector_and_continues_after_corrupt_image(self):
        with fixture_directory() as root:
            source, output = root/"input", root/"output"
            source.mkdir()
            (source/"a-broken.png").write_bytes(b"broken")
            Image.new("RGB", (16, 16), "gray").save(source/"b-empty.png")
            blocked = {"sirmagick.detection": None, "mediapipe": None,
                       "sirmagick.blockface": None, "sirmagick.warpface": None}
            with patch.dict(sys.modules, blocked), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                code = main(["deepfry", str(source), "--output", str(output)])
            self.assertEqual(code, 1)
            report = json.loads((output/"report.json").read_text())
            self.assertEqual([entry["status"] for entry in report["files"]], ["error", "ok"])
            self.assertEqual(report["model_startup_seconds"], 0)
            self.assertEqual(report["files"][1]["detection_seconds"], 0)
            self.assertTrue((output/"b-empty.png.deepfry.png").is_file())
            self.assertFalse((output/"a-broken.png.deepfry.png").exists())
            details = json.loads((output/"b-empty.png.json").read_text())
            self.assertFalse(details["requires_detection"])


if __name__ == "__main__":
    unittest.main()
