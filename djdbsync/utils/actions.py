import inspect
import re
from types import MethodType
from typing import Dict, List, Tuple, Callable, Iterable

from djdbsync.utils.helper import SingletonMetaclass


class ActionRegistry(metaclass=SingletonMetaclass):

    def __init__(self):
        self.actions: Dict[str, List[Callable]] = {}
        self.description: Dict[str, Tuple[str, str]] = {}
        self.unbound_methods: Dict[str, Dict[str, Callable]] = {}

    @staticmethod
    def _get_object_identifier(obj: Callable) -> str:
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
    def register_command(name: str = None) -> MethodType:
        def _register_command_impl(self: ActionRegistry, func: Callable, name_impl: str = name):
            if not name_impl:
                name_impl = func.__name__
            if name_impl in self.description:
                raise FileExistsError(f"Command {name_impl} already registered")
            self.description[name_impl] = _parse_docstring(func.__doc__) if func.__doc__ else (None, None)
            if ActionRegistry._is_methodreference(func):
                cls_id = ActionRegistry._get_object_identifier(func)
                if cls_id not in self.unbound_methods:
                    self.unbound_methods[cls_id] = {}
                self.unbound_methods[cls_id][name_impl] = func
            else:
                self.actions[name_impl].append(func)

            def _wrapper():
                raise NotImplementedError("Method not callable directly! This method is used as action only!")

            return _wrapper

        # PyLint doesn't recognize that a method is created and returned
        # pylint: disable=no-value-for-parameter
        return _register_command_impl.__get__(ActionRegistry(), ActionRegistry)

    def register_object(self, obj: object):
        name = ActionRegistry._get_object_identifier(obj)
        for action_name, unbound_method in self.unbound_methods.get(name, {}).items():
            if hasattr(unbound_method, '__get__'):
                if action_name in self.actions:
                    self.actions[action_name].append(unbound_method.__get__(obj, obj.__class__))
                else:
                    self.actions[action_name] = [unbound_method.__get__(obj, obj.__class__)]

    def get_commands_desc(self) -> Dict['str', Tuple[str, str]]:
        return self.description

    def get_actions(self) -> Iterable[str]:
        return self.actions.keys()

    def get_action_args(self, name) -> Tuple[List[str], int]:
        for action in self.actions.get(name, []):
            i = inspect.getfullargspec(action)
            args = i.args
            if len(args) > 0 and args[0] == 'self':
                args.pop(0)
            return i.args, (len(i.defaults) if i.defaults else 0)
        return [], 0

    def do_action(self, name: str, *args, **kwargs):
        for action in self.actions.get(name, []):
            try:
                action(*args, **kwargs)
            # pylint: disable=broad-except
            except Exception as err:
                print("While running the action '{}' the following error occurred:".format(name))
                print(repr(err))
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
