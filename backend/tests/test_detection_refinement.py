import unittest
import numpy as np
from PIL import Image
from webapp.app.detection import consolidate
from backend.app.vision.crops import square_pad, onion_crop
from backend.app.models.evidence import decide
from backend.app.config import settings


def detection(box, score=.8, view='640'):
    return {'box': box, 'confidence': score, 'pass': view}


class DetectionRefinementTests(unittest.TestCase):
    def prediction(self, original='grade_a'):
        return {'predicted_class': original, 'scores': {'grade_a': .7, 'damaged': .1, 'rotten': .1, 'sprouted': .1}}

    def evidence(self, kind):
        row = {k: .2 for k in ('whole','dry','cut','injury','rot','shoot','background')}
        row[kind] = .4
        return row

    def test_fresh_cut_overrides_healthy_appearance(self):
        result = decide(self.prediction(), [self.evidence('cut')]*6, settings)
        self.assertEqual(result['condition'], 'damaged')
        self.assertTrue(result['needs_review'])
        self.assertEqual(result['confidence'], result['scores']['damaged'])

    def test_dry_neck_does_not_pass_sprout_check(self):
        views = [self.evidence('shoot')] + [self.evidence('dry')]*5
        self.assertEqual(decide(self.prediction('sprouted'), views, settings)['condition'], 'grade_a')

    def test_repeated_shoots_are_sprouted(self):
        self.assertEqual(decide(self.prediction(), [self.evidence('shoot')]*6, settings)['condition'], 'sprouted')

    def test_decay_distinct_from_fresh_cut(self):
        views = [self.evidence('rot')]*3 + [self.evidence('cut')]*3
        self.assertEqual(decide(self.prediction(), views, settings)['condition'], 'rotten')

    def test_physical_injury_without_decay_is_damaged(self):
        self.assertEqual(decide(self.prediction('rotten'), [self.evidence('injury')]*6, settings)['condition'], 'damaged')

    def test_background_needs_whole_crop_and_repeated_agreement(self):
        self.assertTrue(decide(self.prediction(), [self.evidence('background')]*6, settings)['exclude_from_count'])
        self.assertFalse(decide(self.prediction(), [self.evidence('whole')]+[self.evidence('background')]*5, settings)['exclude_from_count'])

    def test_group_box_is_not_an_extra_onion(self):
        kept, info = consolidate([detection([0, 0, 1, 1]),
                                  detection([.05, .1, .45, .8]),
                                  detection([.55, .1, .95, .8])])
        self.assertEqual(len(kept), 2)
        self.assertEqual(info['group_boxes_removed'], 1)

    def test_duplicate_scales_keep_one_detection_and_both_supports(self):
        kept, _ = consolidate([detection([0, 0, .5, .5]),
                               detection([.01, .01, .49, .49], .7, '1280')])
        self.assertEqual(len(kept), 1)
        self.assertEqual(set(kept[0]['support']), {'640', '1280'})

    def test_touching_distinct_bulbs_remain_separate(self):
        kept, _ = consolidate([detection([0, 0, .55, .6]),
                               detection([.35, 0, .9, .6])])
        self.assertEqual(len(kept), 2)

    def test_empty_and_below_threshold(self):
        self.assertEqual(consolidate([])[0], [])
        self.assertEqual(consolidate([detection([0,0,1,1], .1)])[0], [])

    def test_square_padding_preserves_shoot_at_image_edge(self):
        im = Image.new('RGB', (20, 80), 'red')
        im.putpixel((10, 0), (0, 255, 0))
        padded = square_pad(im)
        self.assertEqual(padded.size, (80, 80))
        self.assertEqual(padded.getpixel((40, 0)), (0, 255, 0))

    def test_context_masks_neighbor_without_erasing_target(self):
        rgb = np.full((100, 100, 3), 255, np.uint8)
        boxes = [{'bbox': [20,20,30,30]}, {'bbox': [45,20,30,30]}]
        crop = np.array(onion_crop(rgb, boxes, 0, .5))
        self.assertTrue((crop[20,42] == 255).all()) # overlapping target remains
        self.assertTrue((crop[20,50] == 127).all()) # neighbor outside target


if __name__ == '__main__':
    unittest.main()
