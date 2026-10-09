from contextlib import contextmanager
import shutil
import unittest
from uuid import uuid4
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from sirmagick.data import Detection, ImageError, NoDetectionError, original_points
from sirmagick.images import detection_image, image_paths, load_image


@contextmanager
def fixture_directory():
    # Normale vererbte Projekt-ACLs statt Windows-Sonderrechten von tempfile.
    root = Path(__file__).resolve().parent / ("fixture-" + uuid4().hex)
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root)


class CoreTests(unittest.TestCase):
    def test_coordinates_use_original_dimensions(self):
        point = original_points([SimpleNamespace(x=0.25, y=0.75, visibility=0.9,
                                                  presence=0.8)], 2000, 1000)[0]
        self.assertEqual((point.x, point.y), (500, 750))
        self.assertEqual(point.visibility, 0.9)

    def test_detection_requirements_are_independent(self):
        result = Detection(100, 100, 100, 100, [[object()]], [], 0.1)
        result.require("face")
        result.require("any")
        with self.assertRaises(NoDetectionError):
            result.require("body")
        with self.assertRaises(ValueError):
            result.require("invalid")

    def test_gif_uses_first_frame(self):
        with fixture_directory() as directory:
            path = Path(directory) / "animation.gif"
            Image.new("RGB", (10, 10), "red").save(
                path, save_all=True, append_images=[Image.new("RGB", (10, 10), "blue")],
                duration=100)
            self.assertEqual(load_image(path).getpixel((0, 0)), (255, 0, 0, 255))

    def test_scaling_transparency_and_original_preserved(self):
        image = Image.new("RGBA", (2000, 1000), (0, 0, 0, 0))
        reduced = detection_image(image, 500)
        self.assertEqual(reduced.size, (500, 250))
        self.assertEqual(reduced.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 0))

    def test_exif_orientation_is_applied(self):
        with fixture_directory() as directory:
            path = Path(directory) / "rotated.jpg"
            exif = Image.Exif()
            exif[274] = 6
            Image.new("RGB", (20, 10)).save(path, exif=exif)
            self.assertEqual(load_image(path).size, (10, 20))

    def test_links_skipped_and_corrupt_image_rejected(self):
        with fixture_directory() as directory:
            root = Path(directory)
            (root / "link.url").write_text("not an image")
            broken = root / "broken.PNG"
            broken.write_bytes(b"not an image")
            self.assertEqual(image_paths(root), [broken])
            with self.assertRaises(ImageError):
                load_image(broken)


if __name__ == "__main__":
    unittest.main()
