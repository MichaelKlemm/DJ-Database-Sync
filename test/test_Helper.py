import unittest

from djdbsync.utils.helper import SingletonMetaclass


class TestSingleton(unittest.TestCase):

    def setUp(self) -> None:
        super(TestSingleton, self).setUp()

    def tearDown(self) -> None:
        super(TestSingleton, self).tearDown()

    def test_createInstance(self):
        """
        A class using the singleton pattern can be initialized
        """
        class Test(metaclass=SingletonMetaclass):
            def __init__(self, a):
                self.data = a

        obj = Test("It works")
        assert obj
        assert obj.data == "It works"

    def test_createOnlyOnce(self):
        """
        Instantiate a class twice will create two equal references to one object.
        """
        class Test(metaclass=SingletonMetaclass):
            def __init__(self):
                self.data = None

        obj1 = Test()
        obj2 = Test()
        assert obj1 == obj2

    def test_createDontOverwriteData(self):
        """
        Data stored by object using the singleton will not be overwritten by a second instantiation
        """
        class Test(metaclass=SingletonMetaclass):
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
        class Test1(metaclass=SingletonMetaclass):
            def __init__(self, data):
                self.data = data

        class Test2(metaclass=SingletonMetaclass):
            def __init__(self, data):
                self.data = data

        obj1 = Test1("Expected")
        obj2 = Test2("Also expected")
        assert obj1.data == "Expected"
        assert obj2.data == "Also expected"

    def test_callMethod(self):
        """
        A object method can be called
        """
        class Test(metaclass=SingletonMetaclass):
            def __init__(self, a, *args, **kwargs):
                self.data = a
            def get_data(self):
                return self.data

        obj = Test("It works")
        assert obj
        assert obj.data == "It works"
        assert obj.get_data() == "It works"
        assert Test("").get_data() == "It works"

    def test_callStaticAndClassMethod(self):
        """
        Class can have static and class methods
        """
        class Test(metaclass=SingletonMetaclass):
            def __init__(self, a):
                assert False
            @staticmethod
            def static_method():
                return "static"
            @classmethod
            def class_method(cls):
                return "class"

        assert Test.static_method() == "static"
        assert Test.class_method() == "class"


if __name__ == '__main__':
    unittest.main()