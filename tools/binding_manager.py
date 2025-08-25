from dataclasses import dataclass
from typing import Optional

from kivy.event import EventDispatcher


@dataclass
class Binding:
    obj: EventDispatcher
    name: str
    fn: callable
    uid: Optional[int] = None

    def bind(self):
        if self.uid is None:
            self.uid = self.obj.fbind(self.name, self.fn)

    def unbind(self):
        if self.uid is not None:
            self.obj.unbind_uid(self.name, self.uid)
            self.uid = None


class BindingManager(object):
    def __init__(self, **kwargs):
        self.bindings: list[Binding] = []
        self.paused_bindings: list[Binding] = []
        super().__init__(**kwargs)

    def bind_item(self, obj:EventDispatcher, name:str, fn:callable):
        binding = Binding(obj=obj, name=name, fn=fn)
        binding.bind()
        self.bindings.append(binding)

    def unbind_item(self, obj:EventDispatcher = None, name: str = None, fn:callable = None, cls = None):
        to_unbind = self.filter_bindings(self.bindings, obj=obj, name=name, fn=fn, cls=cls)
        if to_unbind:
            for binding in to_unbind:
                binding.unbind()
            self.bindings = [b for b in self.bindings if b not in to_unbind]
        return to_unbind

    def unbind_items(self):
        for binding in self.bindings:
            binding.unbind()
        self.bindings = []
        self.paused_bindings = []

    def pause_binding(self, obj:EventDispatcher = None, name: str = None, fn:callable = None, cls = None):
        unbinded = self.unbind_item(obj=obj, name=name, fn=fn, cls=cls)
        self.paused_bindings.extend(unbinded)
        return unbinded

    def pause_bindings(self):
        for binding in self.bindings:
            binding.unbind()
        self.paused_bindings = self.bindings
        self.bindings = []

    def resume_binding(self, obj:EventDispatcher = None, name: str = None, fn:callable = None, cls = None):
        to_resume = self.filter_bindings(self.paused_bindings, obj=obj, name=name, fn=fn, cls=cls)
        if to_resume:
            for binding in to_resume:
                self.bind_item(binding.obj, binding.name, binding.fn)
            self.paused_bindings = [b for b in self.paused_bindings if b not in to_resume]

    def resume_bindings(self):
        for binding in self.paused_bindings:
            binding.bind()
        self.bindings = self.paused_bindings
        self.paused_bindings = []

    @staticmethod
    def filter_bindings(bindings, obj:EventDispatcher = None, name: str = None, fn:callable = None, cls = None):
        return [
            binding for binding in bindings if (
            (cls is None or isinstance(binding.obj, cls)) and
            (obj is None or binding.obj == obj) and
            (fn is None or binding.fn == fn) and
            (name is None or binding.name == name))
        ]
