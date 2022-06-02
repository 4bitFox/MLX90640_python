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
test_buzzer = eval(config.get("Monitor", "monitor_buzzer_enable"))
test_array = eval(config.get("Monitor", "monitor_pixels_array"))
#test_pixels_autosave = True

pixel_trigger = eval(config.get("Monitor", "monitor_autotrigger_enable"))
pixel_trigger_array = eval(config.get("Monitor", "monitor_autotrigger_array"))
frames_keep_amount = int(config.get("Monitor", "monitor_autotrigger_previous_frame"))

emissivity = float(config.get("Accuracy", "emissivity"))
EMISSIVITY_BASELINE = 1

GPIO_TRIGGER = 12
GPIO_BUZZER = 13

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
color_temp_alarm = "red"
color_pixel_trigger = "yellow"
interpolation = str(config.get("View", "interpolation")) #none, nearest, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos

SAVE_PREFIX = str(config.get("Save", "save_prefix"))
SAVE_SUFFIX = str(config.get("Save", "save_suffix"))
SAVE_PATH = str(config.get("Save", "save_path"))
SAVE_FILEFORMAT = str(config.get("Save", "save_format")) #ps, eps, pdf, pgf, png, raw, rgba, svg, svgz, jpg, jpeg, tif, tiff

PRINT_FPS = True
PRINT_SAVE = True
PRINT_PIXEL_TEST = False
PRINT_DEBUG = True
PRINT_VALUEERROR = True
PRINT_CLEAR = False





#Calculate emissivity compensation
e_comp = EMISSIVITY_BASELINE / emissivity
test_array_rows = np.shape(test_array)[0]
SENSOR_SHAPE = (24, 32) #resolution

#Init MLX
if PRINT_DEBUG:
    print("Initialize MLX90640")
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000) #I2C
mlx = adafruit_mlx90640.MLX90640(i2c) #MLX90640
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ #1, 2, 4, 8, 16, 32, 64 HZ possible


#Matplotlib
if PRINT_DEBUG:
    print("Starting Matplotlib")
plt.ion() #Interactive plotting
fig,ax = plt.subplots(figsize=(12, 7)) #Figures & Axes
therm1 = ax.imshow(np.zeros(SENSOR_SHAPE), vmin=0, vmax=60, interpolation=interpolation) #start plot with zeros

fig.canvas.manager.set_window_title(TITLE) #Window title
fig.canvas.manager.window.move(WINDOW_POS_X, WINDOW_POS_Y) #Move window
fig.canvas.manager.window.resize(SCREEN_W, SCREEN_H) #Resize to fit screen
fig.canvas.manager.toolbar.hide() #Hide toolbar
fig.subplots_adjust(left=SPACE_L, bottom=SPACE_B, right=SPACE_R, top=SPACE_T) #Adjust space to border
#fig.canvas.manager.full_screen_toggle() #Fullscreen

#fig.patch.set_facecolor(color_bg) #Background color

plt.xticks([]) #Hide xticks
plt.yticks([]) #Hide yticks

#Define temperature bar
cbar = fig.colorbar(therm1) #Colorbar for temps
#cbar.ax.yaxis.set_tick_params(color=color_fg) #Tick color
#cbar.set_label("Temperature [$^{\circ}$C]", fontsize=14, color=color_fg) #Label
#plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color=color_fg) #Tick labels


def color_theme(fg, bg):
    fig.patch.set_facecolor(bg) #Background color
    
    cbar.ax.yaxis.set_tick_params(color = fg) #Tick color
    cbar.set_label("Temperature [$^{\circ}$C]", fontsize = 14, color = fg) #Label
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color = fg) #Tick labels
    
color_theme(color_fg, color_bg)


save_queued = False
def save_queue():
    global save_queued
    save_queued = True
    
def save_now():
    global save_queued
    filename = SAVE_PATH + "/" + SAVE_PREFIX + datetime() + SAVE_SUFFIX + "." + SAVE_FILEFORMAT
    plt.savefig(filename, format = SAVE_FILEFORMAT, facecolor = color_bg)
    if PRINT_SAVE:
        print("Saved " + filename)
    save_queued = False
    sleep(1)

#GPIO capture button
def trigger_callback(pin):
    save_queue()
    if PRINT_DEBUG:
        print("GPIO " + str(pin) + " Button pressed.")

GPIO.setup(GPIO_TRIGGER, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Button
GPIO.add_event_detect(GPIO_TRIGGER, GPIO.FALLING, callback=trigger_callback)


#GPIO PWM buzzer
GPIO.setup(GPIO_BUZZER, GPIO.OUT)
def buzz(freq, time):
    buzzer = GPIO.PWM(GPIO_BUZZER, freq)
    buzzer.start(50) #Start with 50% duty cycle
    sleep(time)
    buzzer.stop()


def datetime():
    dt = time.strftime("%Y-%m-%d_%H-%M-%S")
    return dt
        

alarm_state = False
def temp_alarm(alarm):
    global alarm_state
    if alarm:
        if not alarm_state:
            color_theme(color_bg, color_temp_alarm)
            if test_buzzer == True:
                buzz(600, 5)
            alarm_state = True
    else:
        if alarm_state:
            color_theme(color_fg, color_bg)
            alarm_state = False
    

def measurement_points(data_array, test_array): #If all pixels in range return True
    pixels_results = []
    #           Yt  Xl  Min Max
    for row in range(test_array_rows):
        pixel_tested = test(data_array,  test_array[row][0],  test_array[row][1], test_array[row][2], test_array[row][3])
        pixels_results.append(pixel_tested)
    if False in pixels_results:
        return False
    else:
        return True


def test(pixel, row, column, temp_min, temp_max):
    
    if pixel[row, column] > temp_min and pixel[row, column] < temp_max:
        if PRINT_PIXEL_TEST:
            print("Pixel [" + str(row) + "][" + str(column) + "] ok.")
        return True
    else:
        if PRINT_PIXEL_TEST:
            print("Pixel [" + str(row) + "][" + str(column) + "] deviating! Should be " + str(temp_min) + " °C - " + str(temp_max) + " °C . Is " + str(round(pixel[row, column], 1)) + " °C!")
        return False


def update_view(array):
        therm1.set_data(array)
        therm1.set_clim(vmin=np.min(array), vmax=np.max(array)) #set bounds
        
        cbar.update_normal(therm1) #update colorbar range
        
        if not temp_range or temp_min > temp_range_min and temp_max < temp_range_max:
            plt.title(f"Max Temp: {np.max(data_array):.1f} °C    Avg Temp: {np.average(data_array):.1f} °C    Min Temp: {np.min(data_array):.1f} °C", color=color_fg)
        elif temp_min < temp_range_min and temp_max < temp_range_max:
            plt.title(f"Max Temp: {np.max(data_array):.1f} °C            *Min Temp: < {np.min(data_array):.1f} °C  ({temp_min:.1f} °C)", color=color_fg)
        elif temp_min > temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {np.max(data_array):.1f} °C  ({temp_max:.1f} °C)            Min Temp: {np.min(data_array):.1f} °C", color=color_fg)
        elif temp_min < temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {np.max(data_array):.1f} °C  ({temp_max:.1f} °C)        *Min Temp: < {np.min(data_array):.1f} °C  ({temp_min:.1f} °C)", color=color_fg)
        
        plt.pause(0.001) #required





#Loop
if PRINT_DEBUG:
    print("Starting loop")
    
autosave_triggered = False
    
frame = np.zeros((SENSOR_SHAPE[0]*SENSOR_SHAPE[1], )) #setup array for storing all 768 temperatures
t_array = []
data_array_keep = []
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
        data_array = np.reshape(data_array, SENSOR_SHAPE) #Reshape to 24x32
        data_array = np.fliplr(data_array) #Flip left to right
        
        update_view(data_array)
        
        if test_pixels:
            temp_alarm(not measurement_points(data_array, test_array))
#            test_pixels_result = measurement_points(data_array, test_array)
#            temp_alarm(not test_pixels_result)
#        
#            if test_pixels_save:
#                if not autosave_triggered:
#                    if PRINT_SAVE:
#                        print("Automatically saving current picture...")
#                        autosave_triggered = True
#                        save_now()
#                else:
#                    if test_pixels_result:
#                        autosave_triggered = False
        
        if save_queued:
            save_now()
            color_theme(color_bg, color_fg)
            update_view(data_array)
            color_theme(color_fg, color_bg)
        
        
        if pixel_trigger:
            #Store previous frames
            data_array_keep.append(data_array)
            if len(data_array_keep) > frames_keep_amount + 1:
                data_array_keep.pop(0)
            
            #Test pixels & save
            if measurement_points(data_array, pixel_trigger_array):
                if not autosave_triggered:
                    if PRINT_SAVE:
                        print("Automatically saving previous picture...")
                    autosave_triggered = True
                    update_view(data_array_keep[0])
                    save_now()
                    color_theme(color_bg, color_pixel_trigger)
                    update_view(data_array_keep[0])
                    if not alarm_state:
                        color_theme(color_fg, color_bg)
                    else:
                        color_theme(color_bg, color_temp_alarm)
            else:
                if autosave_triggered:
                    autosave_triggered = False
                    
        
        if PRINT_CLEAR:
            os.system("clear")
        
        if PRINT_FPS:
            t_array.append(time.monotonic()-t1)
            print("Sample Rate: {0:2.1f}fps".format(len(t_array)/np.sum(t_array)))
            
    except ValueError:
        if PRINT_VALUEERROR:
            print("ValueError")
             
        continue # if error, just read again
