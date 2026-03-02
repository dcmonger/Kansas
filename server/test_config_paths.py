import unittest

from server import config


class ConfigPathsTest(unittest.TestCase):
    def test_cache_path_is_served_from_repo_root(self):
        self.assertFalse(config.kCachePath.startswith('..'))

    def test_db_path_is_local_to_repo(self):
        self.assertFalse(config.kDBPath.startswith('..'))


if __name__ == '__main__':
    unittest.main()
