class objectify(object):
    '''this class is for superclassing only,
        to save repetetive typing during development
    '''

    def __init__(self, *args, **kwargs):
        super(objectify, self).__init__()


class object_caller(object):
    '''
        This class allows one to create objects without having to pass the options repetetively

        eg.
        class A(object):
            @staticmethod
            def a(self, **kwargs):
                value = kwargs.get('value', None)

        instead of this:
            A.a( value = 'some_value' )

        like this:
            object_caller( value = 'some_value' )( A.a )
    '''
    kw = {}

    def __init__( self, *args, **kwargs ):
        self.kw = kwargs

    def __call__( self, obj, **kw ):
        if callable(obj):
            self.kw.update(**kw)
            return obj(**self.kw)
        else:
            return None
