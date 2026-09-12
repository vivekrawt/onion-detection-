import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from annotate import inventory, normalized_box

class AnnotationTests(unittest.TestCase):
    def test_exact_health_folder_matching(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for cls in ['Healthy','Unhealthy']:
                p = root/cls/'Mixed'/'same.jpg'
                p.parent.mkdir(parents=True)
                p.touch()
            self.assertEqual([x[2] for x in inventory(root)], [0,1])

    def test_coordinates_clipped_to_image(self):
        self.assertEqual(normalized_box([-10,0,110,50],100,100),[0.5,0.25,1.0,0.5])
        self.assertIsNone(normalized_box([50,0,40,50],100,100))
        self.assertIsNone(normalized_box([float('nan'),0,40,50],100,100))

if __name__ == '__main__':
    unittest.main()
