# Implements simple persistence of namespaces via leveldb.

import pickle
import sqlite3

try:
    import leveldb  # type: ignore
except ImportError:
    leveldb = None


class _SQLiteCompatDB:
    """Minimal LevelDB-compatible wrapper used when python-leveldb is absent."""

    def __init__(self, db_path):
        # Namespace passes a directory-like path. Store sqlite DB within it.
        import os

        os.makedirs(db_path, exist_ok=True)
        sqlite_path = os.path.join(db_path, 'kansas.sqlite3')
        self.conn = sqlite3.connect(sqlite_path)
        self.conn.execute(
            'CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v BLOB NOT NULL)'
        )
        self.conn.commit()

    def Put(self, key, value):
        self.conn.execute('INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)', (key, value))
        self.conn.commit()

    def Delete(self, key):
        self.conn.execute('DELETE FROM kv WHERE k = ?', (key,))
        self.conn.commit()

    def Get(self, key):
        row = self.conn.execute('SELECT v FROM kv WHERE k = ?', (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return row[0]

    def RangeIter(self, start, end):
        rows = self.conn.execute(
            'SELECT k, v FROM kv WHERE k >= ? AND k < ? ORDER BY k ASC', (start, end)
        ).fetchall()
        for k, v in rows:
            yield k, v

    def GetStats(self):
        count = self.conn.execute('SELECT COUNT(*) FROM kv').fetchone()[0]
        return f'storage=sqlite3 entries={count}'


_databases = {}
def _GetDB(dbPath):
    """Returns or creates a key/value DB instance stored at dbPath."""

    if dbPath not in _databases:
        if leveldb is not None:
            _databases[dbPath] = leveldb.LevelDB(dbPath)
        else:
            _databases[dbPath] = _SQLiteCompatDB(dbPath)
    return _databases[dbPath]


_meta = {}
def _GetMeta(dbPath):
    """Returns the meta table, which is a list of all other tables."""

    if dbPath not in _meta:
        _meta[dbPath] = Namespace(dbPath, '__META__', version=0)
    return _meta[dbPath]


def ListNamespaces(dbPath):
    """Lists all namespaces registered in the meta table."""

    meta = _GetMeta(dbPath)
    return list(meta)


class Namespace(object):
    """Returns a named, versioned subpartition of a LevelDB instance."""

    def __init__(self, dbpath, name, version=0, serializer=pickle, _prefix=''):
        if ':' in name:
            raise ValueError("name must not contain ':'")
        self.dbpath = dbpath
        self.db = _GetDB(dbpath)
        self.name = name
        self.version = version
        self.serializer = serializer
        self.prefix = str(_prefix)
        if name != '__META__' and not _prefix:
            meta = _GetMeta(dbpath)
            meta.Put(name, (name, version, str(serializer)))

    def _key(self, key):
        if type(key) not in [str, int, float]:
            raise ValueError("key must be atomic type, was '%s'" % type(key))
        key = str(key)
        prefix = self.prefix and (self.prefix + '\0') or ''
        return '%s.v%d:%s' % (self.name, self.version, prefix + key)

    def _invkey(self, internal_key):
        assert ':' in internal_key
        prefix = self.prefix and (self.prefix + '\0') or ''
        return internal_key.split(':', 1)[1][len(prefix):]

    def Subspace(self, name):
        return Namespace(
            self.dbpath,
            self.name,
            self.version,
            self.serializer,
            self.prefix + '\0' + name)

    def Put(self, key, value):
        self.db.Put(self._key(key), self.serializer.dumps(value))

    def Delete(self, key):
        self.db.Delete(self._key(key))

    def Get(self, key):
        try:
            return self.serializer.loads(self.db.Get(self._key(key)))
        except KeyError:
            return None

    def List(self):
        return list(self)

    def __contains__(self, key):
        return self.Get(key) is not None

    def __iter__(self):
        for k, v in self.db.RangeIter(self._key('\x00'), self._key('\xff')):
            yield self._invkey(k), self.serializer.loads(v)


if __name__ == '__main__':
    path = '../db'
    print(_GetDB(path).GetStats())
    print('-- Namespaces --')
    for name, stats in ListNamespaces(path):
        print(name, stats)
        ns = Namespace(path, name, version=stats[1])
        print("num keys =", len(list(ns)))
        vars()[name] = ns
