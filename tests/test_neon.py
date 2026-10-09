import unittest

import numpy as np
from PIL import Image

from sirmagick.data import Detection
from sirmagick.effects import DETECTION_EFFECTS, apply_effect
from sirmagick.neon import _geometry
from test_chudthor import synthetic_face


class NeonTests(unittest.TestCase):
    def test_geometry_masks_and_draws_both_detected_faces(self):
        detection = Detection(240,180,240,180,[synthetic_face(60,80),synthetic_face(180,80)],[],0)
        face_mask, lines = _geometry(detection,(240,180),(240,180))
        for x in (60,180):
            self.assertGreater(face_mask[80,x],0)
            self.assertGreater(lines[40:115,x-40:x+40].max(),0)
        self.assertEqual(face_mask[0,0],0)

    def test_detected_and_empty_images_keep_alpha_and_input(self):
        image = Image.new('RGBA',(240,180),(110,90,70,175))
        source = np.asarray(image).copy()
        for faces in ([],[synthetic_face(120,80)]):
            detection = Detection(240,180,240,180,faces,[],0)
            for mode in ('tron',):
                self.assertIn(mode,DETECTION_EFFECTS)
                output = np.asarray(apply_effect(image,detection,mode))
                np.testing.assert_array_equal(output[...,3],source[...,3])
                np.testing.assert_array_equal(np.asarray(image),source)
                self.assertFalse(np.array_equal(output,source))
        with self.assertRaises(ValueError):
            apply_effect(image,Detection(1,1,1,1,[],[],0),'tron')
