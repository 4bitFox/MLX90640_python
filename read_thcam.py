#!/bin/python3
import numpy as np
import matplotlib.pyplot as plt
import configparser
import sys



#Read###################################################################
#Read rawfile
try:
    rawfile = sys.argv[1]
    raw = configparser.ConfigParser(inline_comment_prefixes=" #")
    raw.read(rawfile)

#Catch no file    
except IndexError:
    print("Missing argument: No file specified!")
    print("Useage: python3 read_thcam.py /example/path/to/file.thcam --export /example/path/to/export.png")
    print("                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^ °°°°°°°° °°°°°°°°°°°°°°°°°°°°°°°°°°°")
    print("                              ^^REQUIRED                  °°optionally export image.")
    sys.exit(1)


try:
    export = sys.argv[2]
    export_path = sys.argv[3]
except IndexError:
    export = False



#Variables##############################################################
#Window parameters
TITLE = "Thermal Camera Viever"
SCREEN_W = 800
SCREEN_H = 480
SPACE_L = 0.05
SPACE_B = 0.025
SPACE_R = 0.95
SPACE_T = 0.95


#Appearance
COLOR_BG = "black"
COLOR_FG = "white"
interpolation = "gaussian" #none, nearest, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos
fullscreen = False


#Console output
PRINT_DEBUG = True



#Read file into vars
FILE_VERSION = float(raw.get("File", "version"))
if FILE_VERSION == 1:
    #Emissivity
    emissivity = float(raw.get("Settings", "emissivity"))
    EMISSIVITY_BASELINE = float(raw.get("Settings", "emissivity_baseline"))
    
    frame_array = np.array(eval(raw.get("Frame", "frame")))
    temp_range_min = float(raw.get("Frame", "temp_range_min"))
    temp_range_max = float(raw.get("Frame", "temp_range_max"))
    
    SENSOR_SHAPE = (np.shape(frame_array)) #resolution of frame
    
    e_comp = EMISSIVITY_BASELINE / emissivity #Emissivity compensation
    frame_array *= e_comp #Correct temperature

else:
    print("File version " + str(FILE_VERSION) + " not supported!")
    


#View###################################################################
#Set up window
if PRINT_DEBUG:
    print("Setting up Matplotlib")
plt.ion() #Interactive plotting
try:
    fig,ax = plt.subplots(figsize=(12, 7)) #Subplots
    fig.canvas.manager.set_window_title(TITLE) #Window title
    #fig.canvas.manager.toolbar.hide() #Hide toolbar
    fig.subplots_adjust(left=SPACE_L, bottom=SPACE_B, right=SPACE_R, top=SPACE_T) #Adjust space to border
    if fullscreen:
        fig.canvas.manager.full_screen_toggle() #Fullscreen
    else:
        fig.canvas.manager.window.resize(SCREEN_W, SCREEN_H) #Resize to fit screen
except AttributeError:
    pass
    #print("Matplotlib AttributeError") #Windows
    
plt.xticks([]) #Hide xticks
plt.yticks([]) #Hide yticks


#Preview and Tepmerature bar
therm1 = ax.imshow(np.zeros(SENSOR_SHAPE), vmin=0, vmax=60, interpolation=interpolation) #Start plot with zeroes
cbar = fig.colorbar(therm1) #Colorbar for temps


#Change color theme
color_fg_set = COLOR_FG #Store for update_view() plt.title color
def color_theme(fg, bg):
    global color_fg_set
    color_fg_set = fg
    
    fig.patch.set_facecolor(bg) #Background color
    
    cbar.ax.yaxis.set_tick_params(color = fg) #Tick color
    cbar.set_label("Temperature [$^{\circ}$C]", fontsize = 14, color = fg) #Label
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color = fg) #Tick labels
    
color_theme(COLOR_FG, COLOR_BG)


#Update view
def update_view(array):
        therm1.set_data(array) #update view
        
        temp_min = np.min(array)
        temp_max = np.max(array)
        
        if temp_min <= temp_range_min:
            tempbar_min = temp_range_min
        else:
            tempbar_min = temp_min
            
        if temp_max >= temp_range_max:
            tempbar_max = temp_range_max
        else:
            tempbar_max = temp_max
        
        therm1.set_clim(vmin = tempbar_min, vmax = tempbar_max) #set bounds
        
        cbar.update_normal(therm1) #update colorbar
        
        #Text above view. Max, Avg, Min
        if temp_min >= temp_range_min and temp_max <= temp_range_max:
            plt.title(f"Max Temp: {temp_max:.1f} °C    Avg Temp: {np.average(array):.1f} °C    Min Temp: {temp_min:.1f} °C", color=color_fg_set)
        elif temp_min < temp_range_min and temp_max <= temp_range_max:
            plt.title(f"Max Temp: {temp_max:.1f} °C            *Min Temp: < {temp_range_min:.1f} °C  ({temp_min:.1f} °C)", color=color_fg_set)
        elif temp_min >= temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {temp_range_max:.1f} °C  ({temp_max:.1f} °C)            Min Temp: {temp_min:.1f} °C", color=color_fg_set)
        elif temp_min < temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {temp_range_max:.1f} °C  ({temp_max:.1f} °C)        *Min Temp: < {temp_range_min:.1f} °C  ({temp_min:.1f} °C)", color=color_fg_set)
        
        plt.pause(0.001) #required



#Display################################################################
if PRINT_DEBUG:
    print("Display Image")
    
update_view(frame_array)
if export == True or export == "-e" or export == "-s" or export == "--export" or export == "--save":
    print("Exporting to: " + str(export_path))
    plt.savefig(export_path)
plt.show(block=True)

