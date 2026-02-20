import tkinter as tk
from src.UI.UI import open_wokwi

root = tk.Tk()
root.title("Wokwi Launcher")
root.geometry("400x200")

tk.Label(root, text="Launch Wokwi Simulator", font=("Arial", 14)).pack(pady=20)
tk.Button(
    root,
    text="Open Wokwi",
    bg="#4CAF50",
    fg="white",
    font=("Arial", 14),
    command=open_wokwi
).pack(pady=10)

root.mainloop()
