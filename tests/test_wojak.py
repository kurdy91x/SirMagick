import unittest

import numpy as np
from PIL import Image

from sirmagick.data import Detection
from sirmagick.effects import apply_effect
from test_chudthor import synthetic_face


class WojakTests(unittest.TestCase):
    def test_chud_anchors_follow_the_same_sampling_map_as_the_face(self):
        from sirmagick.chud_wojak import transformed_points
        angle = .36
        axis = np.array([np.cos(angle),np.sin(angle)])
        down = np.array([-axis[1],axis[0]])
        basis = np.column_stack((axis,down))
        center = np.array([80.,70.])
        region_uv = np.array([[-20,-15],[20,-15],[20,15],[-20,15]])
        region = region_uv@basis.T+center
        points_uv = np.array([[-18,-10],[0,0],[12,8],[70,80]])
        points = points_uv@basis.T+center
        for scale in ((.73,.63),(.90,1.13),(1.42,2.0)):
            target = transformed_points(points,region,*scale,axis,(1.2,1.7))
            uv = (target-center)@basis
            radii = np.array([20,15])*[1.2,1.7]
            radius = np.linalg.norm(uv/(radii*np.maximum(scale,1)),axis=1)
            t = np.clip(radius-1,0,1)
            weight = 1-t*t*(3-2*t)
            recovered = uv/(1+(np.array(scale)-1)*weight[:,None])
            np.testing.assert_allclose(recovered,points_uv,atol=.002)

    def test_npc_moods_change_brows_without_changing_nose_or_mouth(self):
        image = Image.new('RGBA',(160,160),(180,140,110,255))
        detection = Detection(160,160,160,160,[synthetic_face(80,70)],[],0)
        resigned = np.array(apply_effect(image,detection,'wojak_npc'))
        angry = np.array(apply_effect(image,detection,'wojak_npcangry'))
        self.assertFalse(np.array_equal(resigned,angry))
        np.testing.assert_array_equal(resigned[80:],angry[80:])
