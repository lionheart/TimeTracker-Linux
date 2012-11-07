import os, sys

class _Path(object):
    '''
    This class basically makes it so you can run the program outside of the program path
    '''
    _path = ''

    @staticmethod
    def _insert_libs_path( path, idx=0 ):
        '''add path to index idx
            path - abs path to libs
            idx - index to insert path at in sys.path
        '''
        _Path._path = path
        sys.path.insert(idx, _Path._path)

    @staticmethod
    def _get_path( path=None ):
        '''set path or get abs path of __file__ if None
            path - must be abs path to libs or None
        '''
        if not path:
            path = os.path.dirname(os.path.abspath(__file__))
        _Path._path = path
        return _Path._path


def get_libs_path( libs_path='.', path=None, idx=0 ):
    '''insert path to libs at index
        libs_path - relative path to libs
        path - abs path of __file__
    '''
    _Path._insert_libs_path('%s/%s' % ( _Path._get_path(path), libs_path), idx)
