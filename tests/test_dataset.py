import unittest
import tempfile
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_dataset import allocate, check_label, UnionFind

class DatasetTests(unittest.TestCase):
    def test_grouping_and_class_balance(self):
        groups={f'{c}-{i}':[{'class_id':c}]*10 for c in [0,1] for i in range(10)}
        assignments=allocate(groups)
        self.assertEqual(assignments,allocate(groups))
        for c in [0,1]:
            for split,expected in [('train',8),('validate',1),('test',1)]:
                self.assertEqual(sum(assignments[f'{c}-{i}']==split for i in range(10)),expected)

    def test_label_validation(self):
        self.assertEqual(check_label('1 0.5 0.5 1 1',1),1)
        for bad in ['','0 0.5 0.5 1 1','1 nan 0.5 1 1','1 0.1 0.5 1 1']:
            with self.assertRaises(ValueError):
                check_label(bad,1)

    def test_duplicate_union(self):
        uf=UnionFind()
        uf.union('a','b')
        uf.union('b','c')
        self.assertEqual(uf.find('a'),uf.find('c'))

    def test_package_and_validate_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            annotations=base/'annotations'
            (annotations/'records').mkdir(parents=True)
            (annotations/'labels').mkdir()
            source=base/'source'
            source.mkdir()
            for i in range(40):
                cls=i//20
                name=['healthy','unhealthy'][cls]
                image=source/f'{i}.jpg'
                image.write_bytes(f'fixture-{i}'.encode())
                label=annotations/'labels'/f'{i}.txt'
                label.write_text(f'{cls} 0.5 0.5 0.5 0.5\n')
                record={'source':str(image),'relative_path':f'{name}/onion{i:04d}.jpg','class_id':cls,'class_name':name,'status':'needs_review','boxes':[{}],'label':str(label)}
                if i==0:
                    record.update(status='no_detection',boxes=[])
                    record.pop('label')
                (annotations/'records'/f'{i}.json').write_text(json.dumps(record))
            (annotations/'inventory.json').write_text(json.dumps({'total_images':40}))
            (annotations/'run.json').write_text('{}')
            repo=Path(__file__).resolve().parents[1]
            output=base/'dataset'
            subprocess.run([sys.executable,str(repo/'scripts'/'build_dataset.py'),'--annotations',str(annotations),'--output',str(output),'--block-size','2'],check=True,capture_output=True)
            subprocess.run([sys.executable,str(repo/'scripts'/'validate_dataset.py'),str(output)],check=True,capture_output=True)
            result=json.loads((output/'validation.json').read_text())
            self.assertEqual(result['paired_images'],39)
            self.assertTrue(result['passed'])

if __name__=='__main__':
    unittest.main()
