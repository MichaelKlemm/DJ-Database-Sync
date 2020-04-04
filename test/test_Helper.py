import unittest

from djdbsync.utils.Helper import Singleton

class TestSingleton(unittest.TestCase):

    def setUp(self) -> None:
        super(TestSingleton, self).setUp()

    def tearDown(self) -> None:
        super(TestSingleton, self).tearDown()

    def test_createInstance(self):
        """
        A class using the singleton pattern can be initialized
        """
        @Singleton
        class Test(object):
            def __init__(self, a):
                self.data = a

        obj = Test("It works")
        assert obj
        assert obj.data == "It works"

    def test_createOnlyOnce(self):
        """
        Instantiate a class twice will create two equal references to one object.
        """
        @Singleton
        class Test(object):
            def __init__(self):
                self.data = None

        obj1 = Test()
        obj2 = Test()
        assert obj1 == obj2

    def test_createDontOverwriteData(self):
        """
        Data stored by object using the singleton will not be overwritten by a second instantiation
        """
        @Singleton
        class Test(object):
            def __init__(self, data):
                self.data = data

        obj1 = Test("Expected")
        obj2 = Test("Ignored")
        assert obj1.data == "Expected"
        assert obj1.data == obj2.data

    def test_createDifferentClasses(self):
        """
        The singleton decorator can be used by different classes, each creating there own unique instance
        """
        @Singleton
        class Test1(object):
            def __init__(self, data):
                self.data = data

        @Singleton
        class Test2(object):
            def __init__(self, data):
                self.data = data

        obj1 = Test1("Expected")
        obj2 = Test2("Also expected")
        assert obj1.data == "Expected"
        assert obj2.data == "Also expected"


if __name__ == '__main__':
    unittest.main()