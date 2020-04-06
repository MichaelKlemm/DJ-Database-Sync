import kivy
kivy.require('1.0.7')

from kivy.app import App
from kivy.core.window import Window

class MainApp(App):

    def __init__(self):
        Window.size = (410, 600)
        super(MainApp, self).__init__()
        self.title = "DJ-Database Sync"
