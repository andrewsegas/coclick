import tkinter as tk

class Quadrado:
    start_x = 600
    start_y = 250
    end_x   = 1283
    end_y   = 670
    
    def __init__(self):
        a = 1

    def start(self, master=None):
        self.create_rectangle(master)
        
    def on_button_close(self, event):
        self.root.destroy()
        
    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_button_release(self, event):
        if self.start_x < event.x:
            self.end_x = event.x
        else:
            self.end_x = self.start_x
            self.start_x = event.x
        
        if self.start_y < event.y:
            self.end_y = event.y
        else:
            self.end_y = self.start_y
            self.start_y = event.y
        
        self.root.destroy()
        #self.create_rectangle()
        
    def on_key_press(self, event):
        if event.keysym == "Escape":  # Verifica se a tecla pressionada é "Esc"
            self.root.destroy()


    def create_rectangle(self, master=None):

        # Use a Toplevel (blocking via wait_window) when embedded in an existing
        # tkinter app; fall back to a standalone Tk()+mainloop() when run alone.
        if master is not None:
            self.root = tk.Toplevel(master)
        else:
            self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.1)  # Define a transparência da janela (0.0 - totalmente transparente, 1.0 - opaco)
        self.root.attributes("-topmost", True)
        canvas = tk.Canvas(self.root)
        canvas.create_rectangle(self.start_x, self.start_y, self.end_x, self.end_y, outline="green", width=5)
        canvas.pack(fill=tk.BOTH, expand=True)

        canvas.bind("<ButtonPress-1>", self.on_button_press)
        canvas.bind("<ButtonRelease-1>", self.on_button_release)
        canvas.bind("<ButtonPress-3>", self.on_button_close)  # Botão direito do mouse

        if master is not None:
            self.root.grab_set()
            master.wait_window(self.root)
        else:
            self.root.mainloop()

        if self.start_x is not None and self.start_y is not None and self.end_x is not None and self.end_y is not None:
            print("Posição inicial (x, y):", self.start_x, self.start_y)
            print("Posição final (x, y):", self.end_x, self.end_y)