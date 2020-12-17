from tkinter import *
from tkinter import filedialog
from PIL import ImageTk, Image
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import imageio
import cv2

from seam_carving import *
#from seam_carving_main import *

root = Tk()
root.title("Image Smart Resizing")
root.geometry("1050x700")

canvas = Canvas(root, height=400, width=600, highlightthickness=3, highlightbackground="grey")
canvas.grid(row=0, column=0)
width = canvas.winfo_width()
height = canvas.winfo_height()

"""
Global variables
"""
img = None
img_filename = None
img_array = None
energy = None
energy_img = None
seam_img = None
img_width_new = None
img_height_new = None
reduced_img = None
img_width_new_enlarge = None
img_height_new_enlarge = None
enlarged_img = None


"""
Load image function. Click button to load image of user's choice.
"""
def load_img():
    canvas.delete("all")    # Clear canvas
    global img_filename
    root.filename = filedialog.askopenfilename(initialdir="/Users/Alina/Documents/Project/Seam_Carving/imgs", title="Select a file", filetypes=(("png files", "*.png"), ("jpg files", "*.jpg"), ("jpeg files", "*.jpeg")))
    img_filename = root.filename
    global img_array
    img_array = np.asarray(Image.open(img_filename))
    global img
    img = ImageTk.PhotoImage(Image.open(img_filename))
    canvas.create_image(300, 200, image=img)
loading_button = Button(root, text="Choose Image", command=load_img)
loading_button.grid(row=1, column=0)


"""
Calculate the energy of the selected image.
"""
def calculate_energy():
    canvas.delete("all")    # Clear canvas
    global energy
    energy = energy_function(img_array)
    imageio.imwrite("/Users/Alina/Documents/Project/Seam_Carving/energy_img.png", energy)   # Turn array to image and save as energy_img.png
    global energy_img
    energy_img = ImageTk.PhotoImage(Image.open("/Users/Alina/Documents/Project/Seam_Carving/energy_img.png"))
    canvas.create_image(300, 200, image=energy_img)
energy_button = Button(root, text="First Step - Calculate Energy", command=calculate_energy)
energy_button.grid(row=2, column=0)


"""
Find the optimal seam to remove using backtracking
"""
def find_seam():
    vcost, vpaths = compute_cost(img_array, energy)
    end = np.argmin(vcost[-1])
    #seam_energy = vcost[-1, end]
    seam_ = backtrack_seam(vpaths, end)

    vseam = np.copy(img_array)
    for row in range(vseam.shape[0]):
        vseam[row, seam_[row], :] = np.array([1.0, 0, 0])

    imageio.imwrite("/Users/Alina/Documents/Project/Seam_Carving/seam_img.png", vseam)
    global seam_img
    seam_img = ImageTk.PhotoImage(Image.open("/Users/Alina/Documents/Project/Seam_Carving/seam_img.png"))
    canvas.create_image(300, 200, image=seam_img)
seam_button = Button(root, text="Second & Third Step - Calculate Cost & Find Optimal Seam", command=find_seam)
seam_button.grid(row=3, column=0)


"""
Reduce - Smart resizing - Prompting user's input on size of the image
"""
def reduce_size_prompt():
    prompt = Label(root, text="Please enter the size of image you want: (Width x Height)")
    prompt.grid(row=5, column=0)
    global img_width_new
    img_width_new = Entry(root)
    img_width_new.grid(row=6, column=0)
    symbol = Label(root, text="X")
    symbol.grid(row=6, column=1)
    global img_height_new
    img_height_new = Entry(root)
    img_height_new.grid(row=6, column=2)
get_size_button = Button(root, text="Fourth Step - Resize Image", command=reduce_size_prompt)
get_size_button.grid(row=4, column=0)


"""
Smart Resizing - reduce size
"""
def reduce_size():
    canvas.delete("all")    # Clear canvas
    wdth = int(img_width_new.get())
    hght = int(img_height_new.get())
    #reduce_width = reduce(img_array, wdth, axis=1, cfunc=compute_forward_cost)
    #reduce_both = reduce(reduce_width, hght, axis=0, cfunc=compute_forward_cost)
    reduce_width = reduce(img_array, wdth, axis=1)
    reduce_both = reduce(reduce_width, hght, axis=0)

    imageio.imwrite("/Users/Alina/Documents/Project/Seam_Carving/reduced_img.png", reduce_both)
    global reduced_img
    reduced_img = ImageTk.PhotoImage(Image.open("/Users/Alina/Documents/Project/Seam_Carving/reduced_img.png"))
    canvas.create_image(300, 200, image=reduced_img)
    prompt = Label(root, text="Image is being saved in the folder as \"reduced_img\".")
    prompt.grid(row=7, column=1)
reduce_button = Button(root, text="Resize!", command=reduce_size)
reduce_button.grid(row=7, column=0)


"""
Enlarge Prompt
"""
def enlarge_size_prompt():
    prompt = Label(root, text="Please enter the size of image you want -- enlarge: (Width x Height)")
    prompt.grid(row=9, column=0)
    global img_width_new_enlarge
    img_width_new_enlarge = Entry(root)
    img_width_new_enlarge.grid(row=10, column=0)
    symbol = Label(root, text="X")
    symbol.grid(row=10, column=1)
    global img_height_new_enlarge
    img_height_new_enlarge = Entry(root)
    img_height_new_enlarge.grid(row=10, column=2)
get_size_button = Button(root, text="Or... Enlarge!", command=enlarge_size_prompt)
get_size_button.grid(row=8, column=0)


"""
Smart Resizing - enlarge size
"""
def enlarge_size():
    canvas.delete("all")    # Clear canvas
    wdth = int(img_width_new_enlarge.get())
    hght = int(img_height_new_enlarge.get())
    enlarged_width = enlarge(img_array, wdth, axis=1)
    enlarged_both = enlarge(enlarged_width, hght, axis=0)

    imageio.imwrite("/Users/Alina/Documents/Project/Seam_Carving/enlarged_img.png", enlarged_both)
    global enlarged_img
    enlarged_img = ImageTk.PhotoImage(Image.open("/Users/Alina/Documents/Project/Seam_Carving/enlarged_img.png"))
    canvas.create_image(300, 200, image=enlarged_img)
    prompt = Label(root, text="Image is being saved in the folder as \"enlarged_img\".")
    prompt.grid(row=11, column=1)
enlarge_button = Button(root, text="Enlarge!", command=enlarge_size)
enlarge_button.grid(row=11, column=0)

root.mainloop()
