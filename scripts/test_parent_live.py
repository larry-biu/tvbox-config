import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
import refresh_bestfan as module

class ParentLiveTests(unittest.TestCase):
    def test_merge_channel_routes(self):
        text = '#EXTM3U\n'
        for i in range(1, 22):
            text += f'#EXTINF:-1 group-title="央视",CCTV-{i}\nhttp://example.org/{i}.m3u8\n'
        text += '#EXTINF:-1,CCTV1\nhttp://backup.example/1.m3u8\n'
        result, count = module.convert(text)
        self.assertEqual(21, count)
        self.assertIn('CCTV1,http://example.org/1.m3u8#http://backup.example/1.m3u8', result)

    def test_bad_update_preserves_previous(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'live').mkdir()
            (root/'live/backup.txt').write_text('last good')
            with patch.object(module,'ROOT',root), patch.object(module.urllib.request,'urlopen',side_effect=OSError('offline')):
                module.refresh('https://example.org/source', 'backup.txt', 'receipt.json')
            self.assertEqual('last good',(root/'live/backup.txt').read_text())

    def test_empty_playlist_is_rejected(self):
        with self.assertRaises(ValueError):module.convert('#EXTM3U\n')
