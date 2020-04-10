import kivy
kivy.require('1.0.7')


class MainApp(kivy.app.App):

    def __init__(self):
        kivy.core.window.Window.size = (410, 600)
        super(MainApp, self).__init__()
        self.title = "DJ-Database Sync"
