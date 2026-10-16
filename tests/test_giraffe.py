import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from sirmagick.data import Detection, Point
from sirmagick.effects import apply_effect
from sirmagick.giraffe import _shift_up, _select_strip, _repeat_band, _scale_band
from test_chudthor import synthetic_face


def face_at(cx):
    return [Point(cx+(p.x-cx)*2,65+(p.y-65)*2) for p in synthetic_face(cx,65)]


class GiraffeTests(unittest.TestCase):
    def test_repetition_inserts_copies_without_resampling_original_rows(self):
        band = np.arange(80,dtype=np.float32).reshape(20,1,4)
        result = _repeat_band(band,8,3,12)
        self.assertEqual(result.shape,(32,1,4))
        np.testing.assert_array_equal(result[:8],band[:8])
        np.testing.assert_array_equal(result[20:],band[8:])
        np.testing.assert_array_equal(result[11:17],np.tile(band[8:11],(2,1,1)))

    def test_strip_selection_prefers_similar_neighboring_rows(self):
        rgb = np.random.default_rng(6).integers(0,256,(20,12,3),dtype=np.uint8)
        rgb[6:10] = (160,120,100)
        alpha = np.ones((20,12),np.float32)
        self.assertEqual(_select_strip(rgb,alpha,2,16,4),6)

    def test_scaling_preserves_horizontal_features_and_premultiplied_edges(self):
        band = np.zeros((8,12,4),np.float32)
        band[:,3:9,:3] = (60,30,15)
        band[:,3:9,3] = .5
        result = _scale_band(band,16)
        self.assertEqual(result.shape,(24,12,4))
        np.testing.assert_array_equal(result[:,0:3],0)
        np.testing.assert_allclose(result[:,3:9],np.broadcast_to(band[:1,3:9],(24,6,4)))

    def test_head_translation_preserves_every_pixel(self):
        pixels = np.random.default_rng(2).integers(0,256,(80,100,4),dtype=np.uint8)
        original = pixels.copy()
        shifted = _shift_up(pixels,17)
        np.testing.assert_array_equal(shifted[:-17],pixels[17:])
        np.testing.assert_array_equal(shifted[-17:],0)
        np.testing.assert_array_equal(pixels,original)

    def test_background_and_torso_outside_edit_stay_exact(self):
        pixels = np.random.default_rng(3).integers(100,220,(200,200,4),dtype=np.uint8)
        pixels[...,3] = 255
        image = Image.fromarray(pixels)
        detection = Detection(200,200,200,200,[face_at(80)],[],0)
        box = (35,20,125,160)
        mask = np.zeros((140,90),np.uint8)
        mask[10:120,10:80] = 255
        with patch('sirmagick.giraffe._foreground',return_value=(box,mask)):
            result = np.array(apply_effect(image,detection,'giraffe'))
        self.assertEqual(result.shape,pixels.shape)
        np.testing.assert_array_equal(result[:,:35],pixels[:,:35])
        np.testing.assert_array_equal(result[:,125:],pixels[:,125:])
        np.testing.assert_array_equal(result[160:],pixels[160:])
        np.testing.assert_array_equal(pixels,np.array(image))

    def test_growth_respects_output_pixel_limit(self):
        image = Image.new('RGBA',(180,180))
        detection = Detection(180,180,180,180,[face_at(55)],[],0)
        with patch('sirmagick.giraffe.MAX_PIXELS',image.width*image.height-1):
            with self.assertRaisesRegex(ValueError,'24 million pixels'):
                apply_effect(image,detection,'giraffe')

    def test_foreground_entering_below_neck_is_not_raised_as_a_shoulder(self):
        pixels = np.full((200,200,4),(90,140,180,255),dtype=np.uint8)
        pixels[120:160,35:125,:3] = (220,80,70)
        detection = Detection(200,200,200,200,[face_at(80)],[],0)
        mask = np.zeros((140,90),np.uint8)
        mask[10:100,10:80] = 255
        mask[100:] = 255
        with patch('sirmagick.giraffe._foreground',return_value=((35,20,125,160),mask)):
            result = np.array(apply_effect(Image.fromarray(pixels),detection,'giraffe'))
        # These columns contain no head/neck; the shoulder only starts lower down.
        np.testing.assert_array_equal(result[100:120,36:40],pixels[100:120,36:40])
