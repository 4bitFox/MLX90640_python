#!/bin/python3
import time, board, busio
from time import sleep
import numpy as np
import RPi.GPIO as GPIO
import adafruit_mlx90640
import matplotlib.pyplot as plt
import configparser
import os
import sys



#Config#################################################################
#Read config file
try:
    config_file = sys.argv[1]
    config = configparser.ConfigParser()
    config.read(config_file)

#Catch no config file    
except IndexError:
    print("Missing argument: No configuration file specified!")
    print("Useage: python3 thcam.py /example/path/to/configfile.ini")
    print("                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    sys.exit(1)



#Variables##############################################################
#Emissivity
emissivity = float(config.get("Accuracy", "emissivity")) #Emissivity
EMISSIVITY_BASELINE = 1 #Correct sensor emissivity baseline. (Should not be necessary)

#Clip temperatures
temp_range = config.get("Temperature_Range", "range_enable") #Temperatures below and above specified values will be ignored and not shown in thermal image if enabled.
temp_range_min = int(config.get("Temperature_Range", "range_min")) #-40 °C
temp_range_max = int(config.get("Temperature_Range", "range_max")) #300 °C

#Monitor temperatures
test_pixels = eval(config.get("Monitor", "monitor_pixels_enable")) #Monitor pixels. If one or more are not in tolerance, turn screen red. Opptinally send PWM signal to a buzzer.
test_buzzer = eval(config.get("Monitor", "monitor_buzzer_enable")) #PWM buzzer
test_array = eval(config.get("Monitor", "monitor_pixels_array")) #Array of pixels to be tested
#test_pixels_autosave = True

#Auto trigger
pixel_trigger = eval(config.get("Monitor", "monitor_autotrigger_enable")) #If ALL pixels in specified range. Save the oldest frame stored. See: frames_keep_amount. Set to 0 for current frame.
pixel_trigger_array = eval(config.get("Monitor", "monitor_autotrigger_array")) #Which pixels to test.
frames_keep_amount = int(config.get("Monitor", "monitor_autotrigger_previous_frame")) #Number of past frames to keep.

#Window parameters
TITLE = "Thermal Camera"
SCREEN_W = 800
SCREEN_H = 480
WINDOW_POS_X = -2
WINDOW_POS_Y = -30
SPACE_L = 0.05
SPACE_B = 0.025
SPACE_R = 0.95
SPACE_T = 0.95

#GPIO pin numbers
GPIO_TRIGGER_1 = 12
GPIO_TRIGGER_2 = 26
GPIO_BUZZER = 13

#Appearance
COLOR_BG = "black"
COLOR_FG = "white"
COLOR_TEMP_ALARM = "red"
COLOR_PIXEL_TRIGGER = "yellow"
interpolation = str(config.get("View", "interpolation")) #none, nearest, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos
fullscreen = False

#Save
SAVE_PREFIX = str(config.get("Save", "save_prefix"))
SAVE_SUFFIX = str(config.get("Save", "save_suffix"))
SAVE_PATH = str(config.get("Save", "save_path"))
SAVE_FILEFORMAT = str(config.get("Save", "save_format")) #ps, eps, pdf, pgf, png, raw, rgba, svg, svgz, jpg, jpeg, tif, tiff

#Console output
PRINT_FPS = True
PRINT_SAVE = True
PRINT_PIXEL_TEST = False
PRINT_DEBUG = True
PRINT_VALUEERROR = True
PRINT_CLEAR = False



#MLX90640###############################################################
if PRINT_DEBUG:
    print("Setting up MLX90640")
    
SENSOR_SHAPE = (24, 32) #resolution of Sensor

i2c = busio.I2C(board.SCL, board.SDA, frequency=800000) #GPIO I2C frequency

mlx = adafruit_mlx90640.MLX90640(i2c) #Start MLX90640
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ #Refresh rate 1, 2, 4, 8, 16, 32, 64 HZ possible


e_comp = EMISSIVITY_BASELINE / emissivity #Emissivity compensation
frame_array_new = np.zeros((SENSOR_SHAPE[0]*SENSOR_SHAPE[1], )) #setup array for storing all 768 temperatures
def get_frame():
    mlx.getFrame(frame_array_new) #read MLX temperatures into variable
    frame_array = frame_array_new #Store read frame into variable 
    frame_array *= e_comp #Correct temperature
    temp_min = np.min(frame_array) #Store min temp
    temp_max = np.max(frame_array) #Store max temp
    if temp_range: #If temperatures above and below threshhold should be ignored
        array = np.clip(frame_array, temp_range_min, temp_range_max) #Clip temps above or below specified value
    frame_array = np.reshape(frame_array, SENSOR_SHAPE) #Reshape array to Sensor size. Results in 2D array
    frame_array = np.fliplr(frame_array) #Flip array left to right
    return frame_array, temp_min, temp_max
    

autosave_triggered = False #Store autosave state
frame_store = [] #Create array to store previous frames
def autotrigger(frame_current):
    global autosave_triggered
    global frame_store
    
    #Store previous frames
    frame_store.append(frame_current.copy())
    #frame_store += [frame_current.copy()]
    if len(frame_store) > frames_keep_amount + 1:
        frame_store.pop(0)

        ########################################################################################################################DEBUG
        print(frame_current)
        print("current")
        sleep(1)
        print(frame_store[0])
        print("oldest kept")
        sleep(1)
        print(frame_store[5])
        print("latest kept")
        sleep(1)
        print(frame_store[2])
        print("third  kept")
        sleep(1)
            
    #Test pixels & save
    if measurement_points(frame_current, pixel_trigger_array):
        if not autosave_triggered:
            if PRINT_SAVE:
                print("Automatically saving previous picture...")
            autosave_triggered = True
            update_view(frame_store[0])
            save_now()
            color_theme(COLOR_BG, COLOR_PIXEL_TRIGGER)
            update_view(frame_store[0])
            if not alarm_state:
                color_theme(COLOR_FG, COLOR_BG)
            else:
                color_theme(COLOR_BG, COLOR_TEMP_ALARM)
    else:
        if autosave_triggered:
            autosave_triggered = False



#Save###################################################################
if PRINT_DEBUG:
    print("Setting up GPIO buttons")
#GPIO capture button
def trigger_callback(pin): #called when button pressed
    save_queue()
    if PRINT_DEBUG:
        print("GPIO " + str(pin) + " Button pressed.")
        
def trigger_setup(pin): #Add pin to detect button press
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Button
    GPIO.add_event_detect(pin, GPIO.FALLING, callback=trigger_callback)

trigger_setup(GPIO_TRIGGER_1)
trigger_setup(GPIO_TRIGGER_2)


#Get datetime
def datetime():
    dt = time.strftime("%Y-%m-%d_%H-%M-%S")
    return dt


#Queue a save
save_queued = False #Store save queued state
def save_queue():
    global save_queued
    save_queued = True
   
    
#Save now. Only call from within the loop!
def save_now():
    global save_queued
    filename = SAVE_PATH + "/" + SAVE_PREFIX + datetime() + SAVE_SUFFIX + "." + SAVE_FILEFORMAT
    plt.savefig(filename, format = SAVE_FILEFORMAT, facecolor = COLOR_BG)
    if PRINT_SAVE:
        print("Saved " + filename)
    save_queued = False
    sleep(1)



#Alarm##################################################################
#GPIO PWM buzzer
GPIO.setup(GPIO_BUZZER, GPIO.OUT)
def buzz(freq, time):
    buzzer = GPIO.PWM(GPIO_BUZZER, freq)
    buzzer.start(50) #Start with 50% duty cycle
    sleep(time)
    buzzer.stop()
        

#Sound alarm when alarm = True
alarm_state = False #Store alarm state
def temp_alarm(alarm):
    global alarm_state
    if alarm:
        if not alarm_state:
            color_theme(COLOR_BG, COLOR_TEMP_ALARM)
            if test_buzzer == True:
                buzz(800, 5)
            alarm_state = True
    else:
        if alarm_state:
            color_theme(COLOR_FG, COLOR_BG)
            alarm_state = False
  


#Test pixels############################################################
#Tests one if pixel is in tolerance and returns result. Called from measurement_points()
def test(pixel, row, column, temp_min, temp_max):
    if pixel[row, column] > temp_min and pixel[row, column] < temp_max:
        if PRINT_PIXEL_TEST:
            print("Pixel [" + str(row) + "][" + str(column) + "] ok.")
        return True
    else:
        if PRINT_PIXEL_TEST:
            print("Pixel [" + str(row) + "][" + str(column) + "] deviating! Should be " + str(temp_min) + " °C - " + str(temp_max) + " °C . Is " + str(round(pixel[row, column], 1)) + " °C!")
        return False
    

#Check pixels if in tolerance. Returns True if ALL pixels are in tolerance.
def measurement_points(frame_array, test_array):
    pixels_results = []
    test_array_rows = np.shape(test_array)[0]
    for row in range(test_array_rows):
        pixel_tested = test(frame_array,  test_array[row][0],  test_array[row][1], test_array[row][2], test_array[row][3])
        pixels_results.append(pixel_tested)
    if False in pixels_results:
        return False
    else:
        return True



#View###################################################################
#Set up window
if PRINT_DEBUG:
    print("Setting up Matplotlib")
plt.ion() #Interactive plotting
fig,ax = plt.subplots(figsize=(12, 7)) #Subplots
fig.canvas.manager.set_window_title(TITLE) #Window title
fig.canvas.manager.toolbar.hide() #Hide toolbar
fig.subplots_adjust(left=SPACE_L, bottom=SPACE_B, right=SPACE_R, top=SPACE_T) #Adjust space to border
plt.xticks([]) #Hide xticks
plt.yticks([]) #Hide yticks
if fullscreen:
    fig.canvas.manager.full_screen_toggle() #Fullscreen
else:
    fig.canvas.manager.window.move(WINDOW_POS_X, WINDOW_POS_Y) #Move window
    fig.canvas.manager.window.resize(SCREEN_W, SCREEN_H) #Resize to fit screen


#Preview and Tepmerature bar
therm1 = ax.imshow(np.zeros(SENSOR_SHAPE), vmin=0, vmax=60, interpolation=interpolation) #Start plot with zeroes
cbar = fig.colorbar(therm1) #Colorbar for temps


#Change color theme
def color_theme(fg, bg):
    fig.patch.set_facecolor(bg) #Background color
    
    cbar.ax.yaxis.set_tick_params(color = fg) #Tick color
    cbar.set_label("Temperature [$^{\circ}$C]", fontsize = 14, color = fg) #Label
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color = fg) #Tick labels
    
color_theme(COLOR_FG, COLOR_BG)


#Update view
def update_view(array):
        therm1.set_data(array) #update view
        therm1.set_clim(vmin=np.min(array), vmax=np.max(array)) #set bounds
        
        cbar.update_normal(therm1) #update colorbar
        
        #Text above view. Max, Avg, Min
        if not temp_range or temp_min > temp_range_min and temp_max < temp_range_max:
            plt.title(f"Max Temp: {temp_max:.1f} °C    Avg Temp: {np.average(frame_array):.1f} °C    Min Temp: {temp_min:.1f} °C", color=COLOR_FG)
        elif temp_min < temp_range_min and temp_max < temp_range_max:
            plt.title(f"Max Temp: {temp_max:.1f} °C            *Min Temp: < {np.min(frame_array):.1f} °C  ({temp_min:.1f} °C)", color=COLOR_FG)
        elif temp_min > temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {np.max(frame_array):.1f} °C  ({temp_max:.1f} °C)            Min Temp: {temp_min:.1f} °C", color=COLOR_FG)
        elif temp_min < temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {np.max(frame_array):.1f} °C  ({temp_max:.1f} °C)        *Min Temp: < {np.min(frame_array):.1f} °C  ({temp_min:.1f} °C)", color=COLOR_FG)
        
        plt.pause(0.001) #required



#Loop###################################################################
if PRINT_DEBUG:
    print("Starting loop")
    
t_array = [] #Create array to store refresh rate
while True:
    t1 = time.monotonic() #for calculating refresh rete
    try:
        frame_array, temp_min, temp_max = get_frame()
        
        update_view(frame_array) #Update view
        
        if test_pixels: #If pixels should be tested
            temp_alarm(not measurement_points(frame_array, test_array)) #Check if alarm nets to be activated
#            test_pixels_result = measurement_points(frame_array, test_array)
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
        
        if save_queued: #save if queued
            save_now()
            color_theme(COLOR_BG, COLOR_FG)
            update_view(frame_array)
            color_theme(COLOR_FG, COLOR_BG)
        
        
        if pixel_trigger: #If pixels in specified range should trigger a save
            autotrigger(frame_array)
            ##Store previous frames
            #frame_array_keep.append(frame_array)
            #if len(frame_array_keep) > frames_keep_amount + 1:
            #    frame_array_keep.pop(0)
            #    
            #    ########################################################################################################################DEBUG
            #    print(frame_array)
            #    print("current")
            #    sleep(1)
            #    print(frame_array_keep[0])
            #    print("oldest kept")
            #    sleep(1)
            #    print(frame_array_keep[5])
            #    print("latest kept")
            #    sleep(1)
            #    print(frame_array_keep[2])
            #    print("third  kept")
            #    sleep(1)
            
            #Test pixels & save
            #if measurement_points(frame_array, pixel_trigger_array):
            #    if not autosave_triggered:
            #        if PRINT_SAVE:
            #            print("Automatically saving previous picture...")
            #        autosave_triggered = True
            #        update_view(frame_array_keep[0])
            #        save_now()
            #        color_theme(COLOR_BG, COLOR_PIXEL_TRIGGER)
            #        update_view(frame_array_keep[0])
            #        if not alarm_state:
            #            color_theme(COLOR_FG, COLOR_BG)
            #        else:
            #            color_theme(COLOR_BG, COLOR_TEMP_ALARM)
            #else:
            #    if autosave_triggered:
            #        autosave_triggered = False
                    
        
        if PRINT_CLEAR:
            os.system("clear")
        
        if PRINT_FPS:
            t_array.append(time.monotonic()-t1)
            print("Sample Rate: {0:2.1f}fps".format(len(t_array)/np.sum(t_array)))
            
    except ValueError:
        if PRINT_VALUEERROR:
            print("ValueError")
             
        continue # if error, just read again
