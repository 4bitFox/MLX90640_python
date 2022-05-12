#!/bin/python3
import time, board, busio
from time import sleep
import numpy as np
import RPi.GPIO as GPIO
import adafruit_mlx90640
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import configparser
import os
import sys



#Read config file
try:
    config_file = sys.argv[1]
    config = configparser.ConfigParser()
    config.read(config_file)
    
except IndexError:
    print("Missing argument: No configuration file specified!")
    print("Useage: python3 thcam.py /example/path/to/configfile.ini")
    print("                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    sys.exit(1)



temp_range = config.get("Temperature_Range", "range_enable")
temp_range_min = int(config.get("Temperature_Range", "range_min")) #-40 °C
temp_range_max = int(config.get("Temperature_Range", "range_max")) #300 °C

test_pixels = eval(config.get("Monitor", "monitor_pixels_enable"))
test_array = eval(config.get("Monitor", "monitor_pixels_array"))
test_array_rows = np.shape(test_array)[0] - 1

emissivity = float(config.get("Accuracy", "emissivity"))
EMISSIVITY_BASELINE = 1

GPIO_TRIGGER = 12

TITLE = "Thermal Camera"
SCREEN_W = 800
SCREEN_H = 480
WINDOW_POS_X = -2
WINDOW_POS_Y = -30
SPACE_L = 0.05
SPACE_B = 0.025
SPACE_R = 0.95
SPACE_T = 0.95

color_bg = "black"
color_fg = "white"
interpolation = "gaussian" #none, nearest, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos

SAVE_PREFIX = str(config.get("Save", "save_prefix"))
SAVE_SUFFIX = str(config.get("Save", "save_suffix"))
SAVE_PATH = str(config.get("Save", "save_path"))
SAVE_FILEFORMAT = str(config.get("Save", "save_format"))

PRINT_FPS = True
PRINT_SAVE = True
PRINT_DEBUG = True
PRINT_VALUEERROR = True



def measurement_points(data_array, test_array):
    #           Yt  Xl  Min Max
    test(data_array,  test_array[0][0],  test_array[0][1], test_array[0][2], test_array[0][3])
    test(data_array, 23,  0, 25, 35)



#Calculate emissivity compensation
e_comp = EMISSIVITY_BASELINE / emissivity



#GPIO
def trigger_callback(pin):
    if PRINT_DEBUG:
        print("GPIO " + str(pin) + " Button pressed.")
    save_img(False)

GPIO.setup(GPIO_TRIGGER, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Button
GPIO.add_event_detect(GPIO_TRIGGER, GPIO.FALLING, callback=trigger_callback)



#Init MLX
if PRINT_DEBUG:
    print("Initialize MLX90640")
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000) #I2C
mlx = adafruit_mlx90640.MLX90640(i2c) #MLX90640
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ #1, 2, 4, 8, 16, 32, 64 HZ possible
MLX_SHAPE = (24, 32) #MLX resolution



#Matplotlib
if PRINT_DEBUG:
    print("Starting Matplotlib")
plt.ion() #Interactive plotting
fig,ax = plt.subplots(figsize=(12, 7)) #Figures & Axes
therm1 = ax.imshow(np.zeros(MLX_SHAPE), vmin=0, vmax=60, interpolation=interpolation) #start plot with zeros

fig.canvas.manager.set_window_title(TITLE) #Window title
fig.canvas.manager.window.move(WINDOW_POS_X, WINDOW_POS_Y) #Move window
fig.canvas.manager.window.resize(SCREEN_W, SCREEN_H) #Resize to fit screen
fig.canvas.manager.toolbar.hide() #Hide toolbar
fig.subplots_adjust(left=SPACE_L, bottom=SPACE_B, right=SPACE_R, top=SPACE_T) #Adjust space to border
#fig.canvas.manager.full_screen_toggle() #Fullscreen

fig.patch.set_facecolor(color_bg) #Background color

plt.xticks([]) #Hide xticks
plt.yticks([]) #Hide yticks

#Define temperature bar
cbar = fig.colorbar(therm1) #Colorbar for temps
cbar.ax.yaxis.set_tick_params(color=color_fg) #Tick color
cbar.set_label("Temperature [$^{\circ}$C]", fontsize=14, color=color_fg) #Label
plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color=color_fg) #Tick labels



frame = np.zeros((24*32, )) #setup array for storing all 768 temperatures
t_array = []



def datetime():
    dt = time.strftime("%Y-%m-%d_%H-%M-%S")
    #dt = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return dt


save_now = False #Ewww!
def save_img(action):
    global save_now
    if action:
        filename = SAVE_PATH + "/" + SAVE_PREFIX + datetime() + SAVE_SUFFIX + "." + SAVE_FILEFORMAT
        plt.savefig(filename, format = SAVE_FILEFORMAT, facecolor = color_bg)
        if PRINT_SAVE:
            print("Saved " + filename)
        save_now = False
        sleep(1)
    else:
        save_now = True
        


def test(pixel, row, column, temp_min, temp_max):
    
    if pixel[row, column] > temp_min and pixel[row, column] < temp_max:
        #fig.patch.set_facecolor(color_bg)
        print("Pixel [" + str(row) + "][" + str(column) + "] ok.")
        return True
    else:
        #fig.patch.set_facecolor("red")
        print("Pixel [" + str(row) + "][" + str(column) + "] deviating! Should be " + str(temp_min) + " °C - " + str(temp_max) + " °C . Is " + str(round(pixel[row, column], 1)) + " °C!")
        return False

#Loop
if PRINT_DEBUG:
    print("Starting loop")
while True:
    t1 = time.monotonic()
    try:
        mlx.getFrame(frame) #read MLX temperatures into frame var
        data_array = frame
        data_array *= e_comp
        temp_min = np.min(data_array)
        temp_max = np.max(data_array)
        if temp_range:
            data_array = np.clip(data_array, temp_range_min, temp_range_max) #Clip temps
        data_array = np.reshape(data_array, MLX_SHAPE) #Reshape to 24x32
        data_array = np.fliplr(data_array) #Flip left to right
        
        if test_pixels:
            measurement_points(data_array, test_array)
        
        therm1.set_data(data_array)
        therm1.set_clim(vmin=np.min(data_array), vmax=np.max(data_array)) #set bounds
        cbar.update_normal(therm1) #update colorbar range
        
        #Temp overview
        if not temp_range or temp_min > temp_range_min and temp_max < temp_range_max:
            plt.title(f"Max Temp: {np.max(data_array):.1f} °C    Avg Temp: {np.average(data_array):.1f} °C    Min Temp: {np.min(data_array):.1f} °C", color=color_fg)
        elif temp_min < temp_range_min and temp_max < temp_range_max:
            plt.title(f"Max Temp: {np.max(data_array):.1f} °C            *Min Temp: < {np.min(data_array):.1f} °C  ({temp_min:.1f} °C)", color=color_fg)
        elif temp_min > temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {np.max(data_array):.1f} °C  ({temp_max:.1f} °C)            Min Temp: {np.min(data_array):.1f} °C", color=color_fg)
        elif temp_min < temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {np.max(data_array):.1f} °C  ({temp_max:.1f} °C)        *Min Temp: < {np.min(data_array):.1f} °C  ({temp_min:.1f} °C)", color=color_fg)
            
        plt.pause(0.001) #required
        
        if save_now:
            save_img(True)
            
        t_array.append(time.monotonic()-t1)
        
        if PRINT_FPS:
            print("Sample Rate: {0:2.1f}fps".format(len(t_array)/np.sum(t_array)))
            
    except ValueError:
        if PRINT_VALUEERROR:
            print("ValueError")
             
        continue # if error, just read again
