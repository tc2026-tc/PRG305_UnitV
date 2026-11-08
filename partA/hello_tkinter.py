import tkinter as tk

root = tk.Tk()
root.title("Hello Tkinter - Tenzin Choden (29)")
root.geometry("300x150")

label = tk.Label(root, text="Hello!")
label.pack(pady=10)


def on_click():
    label.config(text="Button clicked!")


button = tk.Button(root, text="Click me", command=on_click)
button.pack()

root.mainloop()