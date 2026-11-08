from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

Window.size = (400, 150)


class HelloApp(App):
    def build(self):
        self.title = "Hello Kivy - Tenzin Choden (29)"
        layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        self.label = Label(text="Hello!")
        button = Button(text="Click me")
        button.bind(on_press=self.on_click)
        layout.add_widget(self.label)
        layout.add_widget(button)
        return layout

    def on_click(self, instance):
        self.label.text = "Button clicked!"


HelloApp().run()