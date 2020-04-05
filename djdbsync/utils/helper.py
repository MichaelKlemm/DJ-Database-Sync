from abc import abstractmethod


class SingletonMetaclass(type):

    __INSTANCES__ = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__INSTANCES__:
            cls.__INSTANCES__[cls] = super(SingletonMetaclass, cls).__call__(*args, **kwargs)
        return cls.__INSTANCES__[cls]


class Visitor:

    @abstractmethod
    def accept(self, obj):
        pass


class Visitable:

    @abstractmethod
    def visit(self, obj: Visitor):
        pass
