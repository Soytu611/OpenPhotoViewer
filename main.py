# My previous apps have a complete lack of documentation (comments), making them impossible to work on after a fashion
# So I'll try to add more comments for this one

from tkinter import *
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from io import BytesIO, StringIO
import win32clipboard
import os
import sys
import send2trash

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running normally
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

def check_ending(path):
    accepted_types = [".png", ".jpg", ".jpeg"]
    is_image = False
    for _type in accepted_types:
        if path.lower().endswith(_type):
            is_image = True
    return is_image

class App:
    def __init__(self):
        # Tk window
        self.WIN = Tk()
        self.WIN.title("OpenPhotoViewer")
        self.WIN.geometry(f"1000x550+{self.WIN.winfo_screenwidth()//2-500}+{self.WIN.winfo_screenheight()//2-225}")
        self.WIN.minsize(width=1000, height=550)
        self.WIN.option_add("*Font", "Courier 10")

        self.tree = ttk.Treeview()
        self.current_image_path = ''

        self.has_loaded_image = False
        self.accepted_types = ["png", "jpg", "jpeg"]
        self.image_angle = 0

        # if main.py is run -> else, if run from cmd prompt with arg -> if
        
        self.folder_icon = ImageTk.PhotoImage(
                Image.open(resource_path("Assets/folder.png")).resize((15, 15))
            )
        self.photo_icon = ImageTk.PhotoImage(
                Image.open(resource_path("Assets/icon.png")).resize((15, 15))
            )
        self.base_icon = ImageTk.PhotoImage(
                Image.open(resource_path("Assets/base.png")))
        
        self.WIN.iconphoto(False, self.photo_icon)

        # !!!Runs the app, don't put anything below it!!!
        #self.run()
        # Changed to if __name__ == "__main__"

    def build_window(self):
        self.build_folder_tree()
        self.build_canvas()
        self.build_menu()

    def build_menu(self):  # Builds the topbar
        self.topbar = Menu(self.WIN)
        self.topbar.add_command(label='🗀 Change Directory', command=self.select_directory)
        
        options = Menu(self.topbar, tearoff = 0)
        self.topbar.add_cascade(label='⚙ Options', menu = options)
        options.add_command(label='↺ Rotate Left', command= lambda: self.rotate_image(90))
        options.add_command(label='↻ Rotate Right', command= lambda: self.rotate_image(-90))
        options.add_command(label='🗘 Refresh Directory', command= lambda: self.refresh_directory())
        self.WIN.config(menu=self.topbar)

    def build_right_click_menu(self, event): # Builds popup menu when right clicking
        self.rc_menu = Menu(self.WIN, tearoff=0, font=("Courier", 10))
        self.rc_menu.add_command(label= "📋  Copy", command= lambda: self.copy())
        self.rc_menu.add_command(label= "🔗  Copy as path", command= lambda: self.copy_path())
        self.rc_menu.add_command(label= "✏️  Rename", command= lambda: self.rename())
        self.rc_menu.add_separator()
        self.rc_menu.add_command(label= "🗑  Delete", command= lambda: self.delete())
        try:
            self.rc_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.rc_menu.grab_release()

    def build_canvas(self): #builds the image canvas (where images are shown)
        self.image_canvas = Canvas(self.right_frame)
        self.image_canvas.pack(side="right", fill="both", expand=True)
        self.image_canvas.update_idletasks()

        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()

        self.image_canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self.base_icon,
            anchor="center"
        )
        self.image_canvas.bind("<MouseWheel>", self.do_zoom)
        self.image_canvas.bind('<ButtonPress-1>', lambda event: self.image_canvas.scan_mark(event.x, event.y))
        self.image_canvas.bind("<B1-Motion>", lambda event: self.image_canvas.scan_dragto(event.x, event.y, gain=1))

    def build_folder_tree(self): #builds folders and files (left)
        paned = PanedWindow(self.WIN, orient="horizontal")
        paned.pack(fill="both", expand=True)

        self.left_frame = Frame(paned)
        self.right_frame = Frame(paned)

        paned.add(self.left_frame, minsize=200)
        paned.add(self.right_frame, minsize=300)

        self.tree = ttk.Treeview(self.left_frame)
        scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical",
                                command=self.tree.yview)

        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<ButtonRelease-1>", self.on_item_selected)
        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<Motion>", self.highlight_row)
        self.tree.tag_configure('highlight', background='lightblue')
        scrollbar.pack(side="left", fill="y")
        self.tree.pack(side="right", fill="both", expand=True)

        root_id = self.tree.insert('', 'end', text=self.get_directory_name(), image=self.folder_icon, open=True)
        dirs = os.listdir(self.path)
        if 'desktop.ini' in dirs:
            dirs.remove('desktop.ini')

        for item in dirs:
            full_path = os.path.join(self.path, item)
            if os.path.isdir(full_path):
                sub_id = self.tree.insert(root_id, 'end', text=item, image=self.folder_icon)
                self.explore_directory(full_path, sub_id)
            else:
                self.tree.insert(root_id, 'end', text=item, image=self.photo_icon, values=(full_path,)) 

    def explore_directory(self, path, parent_id):
        try:
            items = os.listdir(path)
        except PermissionError:
            print(f"Access denied: {path}")
            return
        except OSError:
            print(f"Cannot access: {path}")
            return

        if 'desktop.ini' in items:
            items.remove('desktop.ini')

        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                sub_id = self.tree.insert(parent_id, 'end', text=item, image=self.folder_icon, open=True)
                self.explore_directory(full_path, sub_id)
            elif self.check_if_accepted_type(item):
                self.tree.insert(parent_id, 'end', text=item, image=self.photo_icon, values=(full_path,))
    
    def on_item_selected(self, event):
        self.image_angle = 0
        try:
            selected_item = self.tree.focus()
            full_path = self.tree.item(selected_item, "values")[0]
            self.current_image_path = full_path
            self.image_canvas.delete("all")
            self.original_image = Image.open(full_path)
            self.image_canvas.update_idletasks()

            canvas_width = self.image_canvas.winfo_width()
            canvas_height = self.image_canvas.winfo_height()

            img_width = self.original_image.width
            img_height = self.original_image.height

            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            fit_scale = min(scale_x, scale_y)
            self.scale = min(fit_scale, 1.0)

            new_width = int(img_width * self.scale)
            new_height = int(img_height * self.scale)

            resized = self.original_image.resize((new_width, new_height), Image.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(resized)
            self.image_id = self.image_canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
            self.image_canvas.config(scrollregion=(0, 0, new_width, new_height))
        except IndexError:
            return
        except:
            self.refresh_directory()
            return
        
    def on_mousewheel(self, event):
        self.folder_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def highlight_row(self, event): # tree rows highlighted when hovered over
        self.tree = event.widget
        item = self.tree.identify_row(event.y)
        self.tree.tk.call(self.tree, "tag", "remove", "highlight")
        self.tree.tk.call(self.tree, "tag", "add", "highlight", item)

    def do_zoom(self, event):
        try:
            if not hasattr(self, "original_image"):
                return

            if event.delta > 0:
                self.scale *= 1.1
            else:
                self.scale *= 0.9

            self.scale = max(0.1, min(self.scale, 20))

            new_width = int(self.original_image.width * self.scale)
            new_height = int(self.original_image.height * self.scale)

            resized = self.original_image.resize((new_width, new_height), Image.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(resized)

            self.image_canvas.itemconfig(self.image_id, image=self.tk_image)
            self.image_canvas.config(scrollregion=(0, 0, new_width, new_height))
            self.rotate_image(0)
        except:
            return

    def delete(self):
        self.d_WIN = Toplevel(self.WIN)
        self.d_WIN.geometry(f"270x60+{self.WIN.winfo_screenwidth()//2-135}+{self.WIN.winfo_screenheight()//2-30}")
        self.d_WIN.title("Delete file?")
        self.d_WIN.attributes("-topmost", True)

        
        file_name, file_extension = os.path.splitext(self.selected_photo_path)
        file_name_no_path = os.path.basename(file_name.split('/')[-1])
        if len(file_name_no_path) < 21:
            label_1 = Label(self.d_WIN, text=f"Delete {file_name_no_path}?")
        else:
            label_1 = Label(self.d_WIN, text=f"Delete {file_name_no_path[:21]}...?")

        del_button = Button(self.d_WIN, text="Delete! 🗑", command= lambda: _delete())
        label_1.pack()
        del_button.pack()

        def _delete():
            send2trash.send2trash(f"{file_name}{file_extension}")
            self.refresh_directory()
            self.d_WIN.destroy()

    def rename(self):
        self.r_WIN = Toplevel(self.WIN)
        self.r_WIN.geometry(f"270x60+{self.WIN.winfo_screenwidth()//2-135}+{self.WIN.winfo_screenheight()//2-30}")
        self.r_WIN.title("Rename file")
        self.r_WIN.attributes("-topmost", True)

        file_name, file_extension = os.path.splitext(self.selected_photo_path)
        file_name_no_path = os.path.basename(file_name.split('/')[-1])

        x_button = Button(self.r_WIN, text="X", command= lambda: text_input.delete("1.0", "end"))
        rename_button = Button(self.r_WIN, text="Rename", command=lambda:_rename(text_input.get('1.0', 'end-1c'), file_name, file_extension, 0))

        text_input = Text(self.r_WIN, height=1, width=25)
        text_input.insert(END, file_name_no_path)
        label_1 = Label(self.r_WIN, text=file_extension)


        text_input.grid(column=0, row=1)
        x_button.grid(column=1, row=1)
        rename_button.grid(column=0, row=2)
        label_1.grid(column=2, row=1)

        def _rename(text, file_name, file_extension, index):
            try:
                file_name = file_name.split("\\")
                file_name[-1] = ""
                file_name = "\\".join(file_name)

                if not index:
                    os.rename(self.selected_photo_path, f"{file_name}\\{text}{file_extension}")
                else:
                    os.rename(self.selected_photo_path, f"{file_name}\\{text} ({index}){file_extension}")
                self.refresh_directory()
                self.r_WIN.destroy()

            except FileExistsError:
                _rename(text, file_name, file_extension, index+1)

    def copy(self):
        image = Image.open(self.selected_photo_path)
        output = BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()

        self.send_to_clipboard(win32clipboard.CF_DIB, data)

    def copy_path(self):
        self.WIN.clipboard_clear()
        self.WIN.clipboard_append(self.selected_photo_path)
        self.WIN.update()

    def send_to_clipboard(self, clip_type, data):
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(clip_type, data)
        win32clipboard.CloseClipboard()

    def on_right_click(self, event):
        tree = event.widget
        row_id = tree.identify_row(event.y)
        if row_id:
            try:
                tree.selection_set(row_id)
                self.selected_photo_path = tree.item(row_id)['values'][0]
                self.build_right_click_menu(event)
            except:
                return
        else:
            return

    def check_if_accepted_type(self, file_name):
        return any(file_name.lower().endswith(f".{ext}") for ext in self.accepted_types)

    def get_directory_name(self):
        directory = self.path.split("\\")
        return directory[len(directory) - 1]
    
    def select_directory(self):
        foldername = filedialog.askdirectory(initialdir="/", title="Select a Folder")
        if not foldername:
            return
        self.path = foldername
        for widget in self.WIN.winfo_children():
            widget.destroy()
        self.build_window()
        self.original_image = self.base_icon

    def refresh_directory(self):
        for widget in self.WIN.winfo_children():
            widget.destroy()
        self.build_window()

    def rotate_image(self, angle):
        try:
            self.original_image
        except:
            return
        
        self.image_angle += angle

        rotated_image = self.original_image.rotate(self.image_angle, expand=True)

        img_width, img_height = rotated_image.size
        new_width = int(img_width * self.scale)
        new_height = int(img_height * self.scale)
        rotated_scaled = rotated_image.resize((new_width, new_height), Image.LANCZOS)

        self.tk_image = ImageTk.PhotoImage(rotated_scaled)

        self.image_canvas.delete("all")
        self.image_id = self.image_canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.image_canvas.config(scrollregion=(0, 0, new_width, new_height))

    def load_image(self, path):
        self.image_angle = 0
        try:
            
            self.current_image_path = path
            self.image_canvas.delete("all")
            self.original_image = Image.open(path)
            self.image_canvas.update_idletasks()

            canvas_width = self.image_canvas.winfo_width()
            canvas_height = self.image_canvas.winfo_height()

            img_width = self.original_image.width
            img_height = self.original_image.height

            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            fit_scale = min(scale_x, scale_y)
            self.scale = min(fit_scale, 1.0)

            new_width = int(img_width * self.scale)
            new_height = int(img_height * self.scale)

            resized = self.original_image.resize((new_width, new_height), Image.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(resized)
            self.image_id = self.image_canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
            self.image_canvas.config(scrollregion=(0, 0, new_width, new_height))

        except IndexError:
            return
    
    def run(self): 
        self.build_window()
        if app.has_loaded_image:
            app.load_image(str(sys.argv[1]))
        self.WIN.mainloop()


if __name__ == "__main__":
    app = App()
    if len(sys.argv) > 1:
        if not check_ending(str(sys.argv[1])):
            app.path = str(sys.argv[1])
        else:
            app.path = os.path.dirname(str(sys.argv[1]))
            app.has_loaded_image = True

    else:
        app.path = os.path.join(os.path.expanduser("~"), "Pictures")
    app.run()