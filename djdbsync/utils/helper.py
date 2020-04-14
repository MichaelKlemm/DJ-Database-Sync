from abc import abstractmethod


class SingletonMetaclass(type):

    INSTANCES = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.INSTANCES:
            cls.INSTANCES[cls] = super(SingletonMetaclass, cls).__call__(*args, **kwargs)
        return cls.INSTANCES[cls]

    @classmethod
    def reset(cls, tgt_cls):
        i = cls.INSTANCES.pop(tgt_cls, None)
        if i:
            del i


class Visitor:

    @abstractmethod
    def accept(self, obj):
        pass


class Visitable:

    @abstractmethod
    def visit(self, obj: Visitor):
        pass
