from typing import List
from unittest import TestCase, mock

from djdbsync.utils.actions import ActionRegistry


class TestActionRegistry(TestCase):

    def __init__(self, *args, **kwargs):
        super(TestActionRegistry, self).__init__(*args, **kwargs)

    def setUp(self) -> None:
        super(TestActionRegistry, self).setUp()

    def tearDown(self) -> None:
        ActionRegistry.reset(ActionRegistry)
        super(TestActionRegistry, self).tearDown()

    def test_resolve_function_type(self):

        def aBasicFunction():
            pass

        class ABC:
            @staticmethod
            def aStaticMethod():
                pass
            @classmethod
            def aClassMethod(cls):
                pass
            def aMemberFunction(self):
                pass
            def aMemberFunctionWithoutSelf(s):
                pass

        self.assertEqual(ActionRegistry.get_function_type(aBasicFunction), 'staticfunction')
        self.assertEqual(ActionRegistry.get_function_type(ABC.aStaticMethod), 'staticfunction')
        self.assertEqual(ActionRegistry.get_function_type(ABC.aClassMethod), 'classmethod')
        self.assertEqual(ActionRegistry.get_function_type(ABC.aMemberFunction), 'unboundmethod')

        self.assertEqual(ActionRegistry.get_function_type(ABC().aStaticMethod), 'staticfunction')
        self.assertEqual(ActionRegistry.get_function_type(ABC().aClassMethod), 'classmethod')
        self.assertEqual(ActionRegistry.get_function_type(ABC().aMemberFunction), 'boundmethod')

        self.assertEqual(ActionRegistry.get_function_type('not a function'), 'none')

        # FIXME: Not possible to  differ here :-/
        # self.assertEqual(ActionRegistry.get_function_type(ABC.aMemberFunctionWithoutSelf), 'unboundmethod')

    def test_resolve_base_class_identifier(self):

        class ABC:
            @staticmethod
            def aStaticMethod():
                pass
            @classmethod
            def aClassMethod(cls):
                pass
            def aMemberFunction(self):
                pass

        CLASS_NAME = "test_actions.TestActionRegistry.test_resolve_base_class_identifier.<locals>.ABC"

        self.assertEqual(ActionRegistry.get_baseclass_identifier(ABC), CLASS_NAME)
        self.assertEqual(ActionRegistry.get_baseclass_identifier(ABC.aStaticMethod), CLASS_NAME)
        self.assertEqual(ActionRegistry.get_baseclass_identifier(ABC.aClassMethod), CLASS_NAME)
        self.assertEqual(ActionRegistry.get_baseclass_identifier(ABC.aMemberFunction), CLASS_NAME)

        self.assertEqual(ActionRegistry.get_baseclass_identifier(ABC()), CLASS_NAME)
        self.assertEqual(ActionRegistry.get_baseclass_identifier(ABC().aStaticMethod), CLASS_NAME)
        self.assertEqual(ActionRegistry.get_baseclass_identifier(ABC().aClassMethod), CLASS_NAME)
        self.assertEqual(ActionRegistry.get_baseclass_identifier(ABC().aMemberFunction), CLASS_NAME)

    def test_command_unnamed(self):

        @ActionRegistry.register_command()
        def my_command(a: int, b: str):
            self.assertEqual(a, 1)
            self.assertEqual(b, 'abc')

        self.assertIn("my_command", ActionRegistry().get_actions())
        ActionRegistry().do_action('_my_command', a=1, b='abc')

    def test_command_named(self):

        @ActionRegistry.register_command("cmd")
        def my_command(a: int, b: str, c: int = 8):
            self.assertEqual(a, 4711)
            self.assertEqual(b, 'xyz')

        self.assertIn("cmd", ActionRegistry().get_actions())
        ActionRegistry().do_action('cmd', a=4711, b='xyz')

    def test_command_class(self):

        class ClassWithCommand:
            CALLED = 0

            @classmethod
            @ActionRegistry.register_command("my_command", bind_to_cls=True)
            def my_command(cls, a: int, b: str, c: int = 8):
                self.assertEqual(a, 4711)
                self.assertEqual(b, 'xyz')
                ClassWithCommand.CALLED += 1


        self.assertIn("my_command", ActionRegistry().get_actions())
        ActionRegistry().do_action('my_command', a=4711, b='xyz')
        self.assertEqual(ClassWithCommand.CALLED, 1)

    def test_command_object(self):

        class ClassWithCommand:

            def __init__(self):
                self.a = 0
                self.b = ""
                self.called = 0


            @ActionRegistry.register_command("abc")
            def my_command(self, a: int, b: str, c: int = 8):
                self.a = a
                self.b = b
                self.called += 1

        obj = ClassWithCommand()
        self.assertNotIn("abc", ActionRegistry().get_actions())
        ActionRegistry().register_object(obj)
        self.assertIn("abc", ActionRegistry().get_actions())
        ActionRegistry().do_action('abc', a=4711, b='xyz')

        self.assertEqual(obj.called, 1)
        self.assertEqual(obj.a, 4711)
        self.assertEqual(obj.b, "xyz")

    def test_command_multiple_objects(self):

        class ClassWithCommand:

            def __init__(self):
                self.a = 0
                self.b = ""
                self.called = 0

            @ActionRegistry.register_command("abc")
            def my_command(self, a: int, b: str, c: int = 8):
                self.a = a
                self.b = b
                self.called += 1

        obj1 = ClassWithCommand()
        obj2 = ClassWithCommand()
        ActionRegistry().register_object(obj1)
        ActionRegistry().register_object(obj2)
        ActionRegistry().do_action('abc', a=4711, b='xyz')
        ActionRegistry().do_action('abc', a=4711, b='xyz')

        self.assertEqual(obj1.called, 2)
        self.assertEqual(obj1.a, 4711)
        self.assertEqual(obj1.b, "xyz")

        self.assertEqual(obj2.called, 2)
        self.assertEqual(obj2.a, 4711)
        self.assertEqual(obj2.b, "xyz")

    def test_original_function_not_callable(self):

        @ActionRegistry.register_command()
        def my_command_got_removed():
            self.fail()

        with self.assertRaises(NotImplementedError):
            my_command_got_removed()

    def test_command_name_collision(self):

        @ActionRegistry.register_command("unique")
        def first_method():
            pass

        with self.assertRaises(FileExistsError):
            @ActionRegistry.register_command("unique")
            def second_method():
                pass

    def test_command_args_mismatch(self):

        @ActionRegistry.register_command("run")
        def method(argument: str, something_more: int):
            pass

        with self.assertRaises(RuntimeError):
            ActionRegistry().do_action("run", not_existing=123)

    def test_register_unsupported_function(self):

        class ClassWithStaticMethod1:
            @staticmethod
            @ActionRegistry.register_command()
            def my_static_method1():
                pass

        with self.assertRaises(LookupError):

            class ClassWithStaticMethod2:
                @ActionRegistry.register_command()
                @staticmethod # invalid inner method decoration not using @wraps
                def my_static_method2():
                    pass

    def test_request_args_of_command(self):

        @ActionRegistry.register_command("a")
        def function_command(arg1: int, argN: str, argList: List[str], optArg: bool = False):
            pass

        class CommandHandlerClass:

            @staticmethod
            @ActionRegistry.register_command("b", bind_to_cls=True)
            def static_command(arg1: int, argN: str, argList: List[str], optArg: bool = False):
                pass

            @classmethod
            @ActionRegistry.register_command("c")
            def class_command(cls, arg1: int, argN: str, argList: List[str], optArg: bool = False):
                pass

            @ActionRegistry.register_command("d")
            def common_command(self, arg1: int, argN: str, argList: List[str], optArg: bool = False):
                pass

        obj1 = CommandHandlerClass()
        ActionRegistry().register_object(obj1)
        obj2 = CommandHandlerClass()
        ActionRegistry().register_object(obj2)

        expected_result = (['arg1', 'argN', 'argList', 'optArg'], 1)

        self.assertEqual(ActionRegistry().get_action_args("a"), expected_result)
        self.assertEqual(ActionRegistry().get_action_args("b"), expected_result)
        self.assertEqual(ActionRegistry().get_action_args("c"), expected_result)
        self.assertEqual(ActionRegistry().get_action_args("d"), expected_result)

        self.assertEqual(ActionRegistry().get_action_args("unknown"), ([], 0))

    def test_command_description_parsing(self):

        class CommandHandlerWithDocumentation:

            @ActionRegistry.register_command("command")
            def well_described_command(self, arg1: int, argN: str, argList: List[str], optArg: bool = False):
                """
                This is a short description...

                Separated by two linebreaks,
                this is the long decription

                :param arg1:
                :param argN:
                :param argList:
                :param optArg:
                :return:
                """
                pass

        description = ActionRegistry().get_commands_desc()
        self.assertIn("command", description)
        short, long = description["command"]
        self.assertEqual("This is a short description...", short)
        self.assertEqual("Separated by two linebreaks, this is the long decription", long)
