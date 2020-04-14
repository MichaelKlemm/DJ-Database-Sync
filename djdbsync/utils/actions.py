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
    def get_baseclass_identifier(obj: Callable) -> str:
        i = ""
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            i = '.'.join([obj.__module__, obj.__qualname__.rsplit('.', 1)[0]])
        elif inspect.isclass(obj):
            i = repr(obj).split("'")[1]
        else: # isobject
            i = repr(obj.__class__).split("'")[1]
        return i

    @staticmethod
    def get_function_type(obj: callable) -> str:
        if inspect.ismethod(obj):
            if inspect.isclass(obj.__getattribute__("__self__")):
                return 'classmethod'
            return 'boundmethod'
        if inspect.isfunction(obj):
            # staticfunction or unbound membermethod
            spec = inspect.getfullargspec(obj)
            if len(spec.args) > 0 and spec.args[0] == 'self':
                return 'unboundmethod'
            return 'staticfunction'
        return 'none'

    @staticmethod
    def _parse_docstring(func: Callable) -> Tuple[str, str]:
        if not hasattr(func, "__doc__") or not func.__doc__:
            return None, None
        parts = func.__doc__.split("\n\n")
        parts = [re.sub(r"\s+", " ", i) for i in parts]
        if len(parts) == 1:
            return parts[0].strip(), ""
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
        return "", ""

    @staticmethod
    def register_command(name: str = None, bind_to_cls: bool = False) -> MethodType:
        def _register_command_impl(self: ActionRegistry, func: Callable, name_impl: str = name):
            if not hasattr(func, "__name__") and not hasattr(func, "__qualname__"):
                raise LookupError("Incompatible function {} / not a bare function.".format(repr(func)))
            if not name_impl:
                name_impl = func.__name__
            if name_impl in self.description:
                raise FileExistsError(f"Command {name_impl} already registered")
            self.description[name_impl] = ActionRegistry._parse_docstring(func)
            func_type = ActionRegistry.get_function_type(func)
            if func_type in ('unboundmethod', 'boundmethod'):
                cls_id = ActionRegistry.get_baseclass_identifier(func)
                if cls_id not in self.unbound_methods:
                    self.unbound_methods[cls_id] = {}
                self.unbound_methods[cls_id][name_impl] = func
            elif func_type in ('staticfunction', 'classmethod'):
                if bind_to_cls:
                    cls_id = ActionRegistry.get_baseclass_identifier(func)
                    func = func.__get__(cls_id)
                self.actions[name_impl] = [func]

            def _wrapper():
                raise NotImplementedError("Method not callable directly! This method is used as action only!")

            return _wrapper

        # PyLint doesn't recognize that a method is created and returned
        # pylint: disable=no-value-for-parameter
        return _register_command_impl.__get__(ActionRegistry(), ActionRegistry)

    def register_object(self, obj: object):
        name = ActionRegistry.get_baseclass_identifier(obj)
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
            if len(args) > 0 and args[0] in ('self', 'cls'):
                args.pop(0)
            return i.args, (len(i.defaults) if i.defaults else 0)
        return [], 0

    def do_action(self, name: str, *args, **kwargs):
        for action in self.actions.get(name, []):
            try:
                action(*args, **kwargs)
            # pylint: disable=broad-except
            except Exception as err:
                raise RuntimeError(
                    "While running the action '{}' the following error occurred:\n"
                    "{}\n"
                    "The action is represented by function/method '{}'".format(name, repr(err), action.__qualname__))
