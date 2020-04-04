import inspect
import re
from typing import Dict, List, Tuple, Callable, Iterable


class ActionRegistry(object):
    class Singleton(object):

        __INSTANCE__: object = None

        def __init__(self, func: callable):
            self.func = func

        @classmethod
        def get_instance(cls) -> 'ActionRegistry':
            if not cls.__INSTANCE__:
                cls.__INSTANCE__ = ActionRegistry()
            return cls.__INSTANCE__

        def __call__(self, *args, **kwargs):
            return self.func.__get__(self.__class__.get_instance())(*args, **kwargs)

    def __init__(self):
        self.actions: Dict[str, List[Callable]] = {}
        self.description: Dict[str, Tuple[str, str]] = {}
        self.unbound_methods: Dict[str, Dict[str, Callable]] = {}

    @staticmethod
    def _get_object_identifier(obj) -> str:
        if inspect.isfunction(obj):
            return obj.__qualname__.rsplit('.', 1)[0]
        return obj.__class__.__name__

    @staticmethod
    def _is_methodreference(ptr: callable) -> bool:
        if inspect.ismethod(ptr) or inspect.ismethoddescriptor(ptr):
            return True
        if inspect.isfunction(ptr):
            spec = inspect.getfullargspec(ptr)
            if len(spec.args) > 0 and spec.args[0] == 'self':
                return True
        return False

    @staticmethod
    def register_command(name: str = None):
        def register_command_impl(self, func, i=name):
            if not i:
                 i = func.__name__
            if i in self.description:
                raise FileExistsError(f"Command {i} already registered")
            self.description[i] = _parse_docstring(func.__doc__) if func.__doc__ else (None, None)
            if ActionRegistry._is_methodreference(func):
                cls_id = ActionRegistry._get_object_identifier(func)
                if cls_id not in self.unbound_methods:
                    self.unbound_methods[cls_id] = {}
                self.unbound_methods[cls_id][i] = func
            else:
                self.actions[i].append(func)

            def _wrapper():
                raise NotImplementedError("Method not callable directly! This method is used as action only!")

            return _wrapper

        instance = ActionRegistry.Singleton.get_instance()
        return register_command_impl.__get__(instance, instance.__class__)

    @Singleton
    def register_object(self, obj: object):
        name = ActionRegistry._get_object_identifier(obj)
        for action_name, unbound_method in self.unbound_methods.get(name, {}).items():
            if hasattr(unbound_method, '__get__'):
                if action_name in self.actions:
                    self.actions[action_name].append(unbound_method.__get__(obj, obj.__class__))
                else:
                    self.actions[action_name] = [unbound_method.__get__(obj, obj.__class__)]

    @Singleton
    def get_commands_desc(self) -> Dict['str', Tuple[str, str]]:
        return self.description

    @Singleton
    def get_actions(self) -> Iterable[str]:
        return self.actions.keys()

    @Singleton
    def get_action_args(self, name) -> Tuple[List[str], int]:
        for action in self.actions.get(name, []):
            i = inspect.getfullargspec(action)
            args = i.args
            if len(args) > 0 and args[0] == 'self':
                args.pop(0)
            return i.args, (len(i.defaults) if i.defaults else 0)
        return [], 0

    @Singleton
    def do_action(self, name: str, *args, **kwargs):
        for action in self.actions.get(name, []):
            try:
                action(*args, **kwargs)
            except Exception as e:
                print("While running the action '{}' the following error occurred:".format(name))
                print(repr(e))
                print("The action is represented by function/method '{}'".format(action.__qualname__))


def _parse_docstring(docstring: str) -> Tuple[str, str]:
    parts = docstring.split("\n\n")
    parts = [re.sub(r"\s+", " ", i) for i in parts]
    if len(parts) == 0:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    if len(parts) >= 2:
        return parts[0], parts[1]
