from abc import abstractmethod


class Singleton(object):

    # class SingletonFactory(object):

    def __init__(self, singleton_cls):
        self.instance = None
        self.singleton_cls = singleton_cls

    def __call__(self, *args, **kwargs):
        if not self.instance:
            self.instance = self.singleton_cls(*args,**kwargs)
        return self.instance

    # def __init__(self):
    #     self.factory = None
    #
    # def __call__(self, singleton_cls, *args, **kwargs):


class Visitor(object):

    @abstractmethod
    def accept(self, obj):
        pass


class Visitable(object):

    @abstractmethod
    def visit(self, obj: Visitor):
        pass
