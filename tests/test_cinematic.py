import unittest

import numpy as np
from PIL import Image

from sirmagick.data import Detection
from sirmagick.dealwithit import _mouth_attachment
from sirmagick.effects import apply_effect
from test_chudthor import synthetic_face


class CinematicTests(unittest.TestCase):
    def test_cinematic_preserves_source_alpha_and_supports_tiny_and_repeated_images(self):
        for size in ((1,1), (1,8), (8,1), (90,70)):
            pixels = np.random.default_rng(8).integers(0,256,(size[1],size[0],4),dtype=np.uint8)
            image = Image.fromarray(pixels)
            for mode in ('thermal','nightvision','thanos','tron','rift'):
                result = apply_effect(apply_effect(image,None,mode),None,mode)
                self.assertEqual(result.size,size)
                np.testing.assert_array_equal(np.asarray(result)[...,3],pixels[...,3])
                np.testing.assert_array_equal(np.asarray(image),pixels)

    def test_blunt_mirrors_and_changes_corner_with_face_direction(self):
        points = np.zeros((468,2))
        points[61], points[291] = (30,70), (70,70)
        asset = np.arange(4*8*4,dtype=np.uint8).reshape(4,8,4)
        axis, center = np.array([1.,0.]), np.array([50.,40.])
        points[1] = (35,60)
        left, anchor_left, mouth_left = _mouth_attachment(points,axis,center,40,asset)
        points[1] = (65,60)
        right, anchor_right, mouth_right = _mouth_attachment(points,axis,center,40,asset)
        np.testing.assert_array_equal(left,asset)
        np.testing.assert_array_equal(right,asset[:,::-1])
        np.testing.assert_array_equal(mouth_left,points[61])
        np.testing.assert_array_equal(mouth_right,points[291])
        self.assertGreater(anchor_left[0],anchor_right[0])

    def test_dealwithit_decorates_every_face_and_preserves_alpha(self):
        image = Image.new('RGBA',(240,180),(80,110,140,175))
        detection = Detection(240,180,240,180,[synthetic_face(60,90),synthetic_face(180,90)],[],0)
        result = np.asarray(apply_effect(image,detection,'dealwithit'))
        original = np.asarray(image)
        for x in (60,180):
            self.assertFalse(np.array_equal(result[40:120,x-40:x+40],original[40:120,x-40:x+40]))
        np.testing.assert_array_equal(result[...,3],original[...,3])
