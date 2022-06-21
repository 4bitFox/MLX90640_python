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
    config = configparser.ConfigParser(inline_comment_prefixes=" #")
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

button_1 = bool(config.get("Buttons", "button_1"))
button_2 = bool(config.get("Buttons", "button_2"))

#Clip temperatures
temp_range = config.get("Temperature_Range", "range_enable") #Temperatures below and above specified values will be ignored and not shown in thermal image if enabled.
temp_range_min = int(config.get("Temperature_Range", "range_min")) #-40 °C
temp_range_max = int(config.get("Temperature_Range", "range_max")) #300 °C

#Monitor temperatures
test_pixels = eval(config.get("Monitor", "monitor_pixels_enable")) #Monitor pixels. If one or more are not in tolerance, turn screen red. Opptinally send PWM signal to a buzzer.
test_buzzer = eval(config.get("Monitor", "monitor_buzzer_enable")) #PWM buzzer
test_array = eval(config.get("Monitor", "monitor_pixels_array")) #Array of pixels to be tested

#Auto trigger
pixel_trigger = eval(config.get("Monitor", "monitor_autotrigger_enable")) #If ALL pixels in specified range. Save the oldest frame stored. See: frames_keep_amount. Set to 0 for current frame.
pixel_trigger_array = eval(config.get("Monitor", "monitor_autotrigger_array")) #Which pixels to test.
frames_keep_amount = int(config.get("Monitor", "monitor_autotrigger_previous_frame")) #Number of past frames to keep.

#Overheating alarm
OVERHEAT_DETECTION = True #Detect overheating
OVERHEAT_ALERT = True #Alert when overheating
OVERHEAT_ALERT_TEMP = 88 #Temperature to start alert
OVERHEAT_ALERT_BUZZER = True #Alert with buzzer
OVERHEAT_POWEROFF = True #Poweroff when too hot
OVERHEAT_POWEROFF_TEMP = 90 #Poweroff temp

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
interpolation = str(config.get("View", "interpolation")) #none, nearest, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos
fullscreen = False

#Save
SAVE_IMG = True
SAVE_RAW = True
SAVE_PREFIX = str(config.get("Save", "save_prefix"))
SAVE_SUFFIX = str(config.get("Save", "save_suffix"))
SAVE_PATH = str(config.get("Save", "save_path"))
SAVE_FILEFORMAT = str(config.get("Save", "save_format")) #ps, eps, pdf, pgf, png, raw, rgba, svg, svgz, jpg, jpeg, tif, tiff
SAVE_TEMP_ALARM_VISIBLE = True

#Console output
PRINT_PERFORMANCE = True
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


#Get newest frame
e_comp = EMISSIVITY_BASELINE / emissivity #Emissivity compensation
frame_empty = np.zeros((SENSOR_SHAPE[0], SENSOR_SHAPE[1]))
frame_array_new = np.zeros((SENSOR_SHAPE[0]*SENSOR_SHAPE[1], )) #setup array for storing all 768 temperatures
def get_frame():
    mlx.getFrame(frame_array_new) #read MLX temperatures into variable
    frame_array = frame_array_new #Store read frame into variable 
    frame_array *= e_comp #Correct temperature
    frame_array = np.reshape(frame_array, SENSOR_SHAPE) #Reshape array to Sensor size. Results in 2D array
    frame_array = np.fliplr(frame_array) #Flip array left to right
    return frame_array
    

#Automatically trigger a photo
autosave_triggered = False #Store autosave state
frame_store = [] #Create list to store previous frames
def autotrigger(frame_current):
    global autosave_triggered
    global frame_store
    global save_queued
    
    #Store previous frames
    if frames_keep_amount == 0:
        frame_store = [frame_current]
    else:
        frame_store.append(frame_current.copy()) #Append current frame to the end of list. ".copy()" required!
        if len(frame_store) > frames_keep_amount + 1:
            frame_store.pop(0) #Delete the oldest frame
    
    #Test pixels & save
    if measurement_points(frame_current, pixel_trigger_array):
        if not autosave_triggered:
            if PRINT_SAVE:
                print("Automatically saving picture...")
            autosave_triggered = True
            save_queue(frame_store[0])
    else:
        if autosave_triggered:
            autosave_triggered = False



#Save###################################################################
if PRINT_DEBUG:
    print("Setting up GPIO buttons")
#GPIO capture button
def trigger_callback(pin): #called when button pressed
    try:
        save_queue(frame_array)
    except NameError: #If button is pressed to early, frame_array is not defined yet. Catch and ignore :)
        pass
    if PRINT_DEBUG:
        print("GPIO " + str(pin) + " Button pressed.")
        
def trigger_setup(pin): #Add pin to detect button press
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) #Button
    GPIO.add_event_detect(pin, GPIO.FALLING, callback=trigger_callback)

if button_1:
    trigger_setup(GPIO_TRIGGER_1) #Button 1
if button_2:
    trigger_setup(GPIO_TRIGGER_2) #Button 2


#Get datetime
def datetime():
    dt = time.strftime("%Y-%m-%d_%H-%M-%S")
    return dt


def save_rawfile(frame, filename):
    e_comp_revert = 1 / e_comp
    frame *= e_comp_revert #revert emissivity compensation
    
    #Convert array to stringified list
    frame = str(tuple(frame))
    frame = frame.replace("\n", "").replace(". ", "").replace(" ", "").replace("(", "").replace(")", "").replace("array", "").replace(",", ", ") #Remove unwanted parts
    frame = "[" + frame + "]" #Add missing brackets
    
    
    rawfile = configparser.ConfigParser(inline_comment_prefixes=" #")
    
    rawfile.add_section("File")
    rawfile.set("File", "version", "1 #DO NOT CHANGE!") #Version of file format. Tells the viever to read the file differently, depending on what version it is.
    
    rawfile.add_section("Settings")
    rawfile.set("Settings", "emissivity", str(emissivity))
    rawfile.set("Settings", "emissivity_baseline", str(EMISSIVITY_BASELINE))
    
    rawfile.add_section("Frame")
    rawfile.set("Frame", "frame", frame)
    rawfile.set("Frame", "temp_range_min", str(temp_range_min))
    rawfile.set("Frame", "temp_range_max", str(temp_range_max))
    
    #Save file
    with open(filename + ".thcam", "w") as rawfileObj:
        rawfile.write(rawfileObj)
        rawfileObj.flush()
        rawfileObj.close()


#Queue a save
save_queued = False #Store save queued state
save_queued_frame = frame_empty #Store queued frame
def save_queue(frame): #Queue Save
    global save_queued
    global save_queued_frame
    save_queued = True
    save_queued_frame = frame.copy()
   
    
#Save now. Only call from within the loop!
def save_now(frame):
    global save_queued
    filename = SAVE_PATH + "/" + SAVE_PREFIX + datetime() + SAVE_SUFFIX# + "." + SAVE_FILEFORMAT
    
    if SAVE_IMG:
        color_theme(COLOR_BG, COLOR_FG)
        update_view(frame)
        if SAVE_TEMP_ALARM_VISIBLE and alarm_state:
            color_theme(COLOR_BG, COLOR_TEMP_ALARM)
        else:
            color_theme(COLOR_FG, COLOR_BG)
        update_view(frame)
        plt.savefig(filename + "." + SAVE_FILEFORMAT, format = SAVE_FILEFORMAT)
        if PRINT_SAVE:
            print("Saved " + filename + "." + SAVE_FILEFORMAT)
        if alarm_state:
            color_theme(COLOR_BG, COLOR_TEMP_ALARM)
        
    
    if SAVE_RAW:
        save_rawfile(frame, filename)
        if PRINT_SAVE:
            print("Saved " + filename + ".thcam")
    save_queued = False



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
  

#Get CPU temp
def temp_cpu():
    temp = os.popen("vcgencmd measure_temp").readline() #Read Raspberry Pi temp
    temp = float(temp.replace("temp=", "").replace("'C", "")) #Remove text and convert to float
    return temp


#Protect from overheating
def temp_cpu_protect():
    temp = temp_cpu()
    
    overheat_alert_triggered = False
    while temp >= OVERHEAT_ALERT_TEMP:
        if OVERHEAT_POWEROFF and temp >= OVERHEAT_POWEROFF_TEMP:
            print("Too hot! " + str(temp) + "°C Powering off...")
            os.system("poweroff")
            sleep(10)
            os.system("sudo poweroff")
            os.system("pkill python")
        
        if not OVERHEAT_ALERT:
            break #Exit loop now if alert disabled
            
        overheat_alert_triggered = True
            
        print("Overheating! " + str(temp) + " °C")
        
        color_theme("black", "orange")
        update_view(frame_empty)
        plt.title(f"CAMERA OVERHEATING! CPU: {str(temp)} °C", color="black") #Text above preview
        plt.pause(0.001)
        sleep(1)
        color_theme("black", "red")
        update_view(frame_empty)
        plt.title(f"CAMERA OVERHEATING! CPU: {str(temp)} °C", color="black") #Text above preview
        plt.pause(0.001)
        
        if OVERHEAT_ALERT_BUZZER:
            buzz(800, 5)
            buzz(1200, 5)
            
    
    if overheat_alert_triggered: #Return to normal operation if alert has been triggered
        overheat_alert_triggered = False
        color_theme(COLOR_FG, COLOR_BG)
        
        
        
#Test pixels############################################################
#Tests if pixel is in tolerance and returns result. Called from measurement_points()
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
        
        if temp_range and temp_min <= temp_range_min:
            tempbar_min = temp_range_min
        else:
            tempbar_min = temp_min
            
        if temp_range and temp_max >= temp_range_max:
            tempbar_max = temp_range_max
        else:
            tempbar_max = temp_max
        
        therm1.set_clim(vmin = tempbar_min, vmax = tempbar_max) #set bounds
        
        cbar.update_normal(therm1) #update colorbar
        
        #Text above view. Max, Avg, Min
        if not temp_range or temp_min >= temp_range_min and temp_max <= temp_range_max:
            plt.title(f"Max Temp: {temp_max:.1f} °C    Avg Temp: {np.average(array):.1f} °C    Min Temp: {temp_min:.1f} °C", color=color_fg_set)
        elif temp_min < temp_range_min and temp_max <= temp_range_max:
            plt.title(f"Max Temp: {temp_max:.1f} °C            *Min Temp: < {temp_range_min:.1f} °C  ({temp_min:.1f} °C)", color=color_fg_set)
        elif temp_min >= temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {temp_range_max:.1f} °C  ({temp_max:.1f} °C)            Min Temp: {temp_min:.1f} °C", color=color_fg_set)
        elif temp_min < temp_range_min and temp_max > temp_range_max:
            plt.title(f"*Max Temp: > {temp_range_max:.1f} °C  ({temp_max:.1f} °C)        *Min Temp: < {temp_range_min:.1f} °C  ({temp_min:.1f} °C)", color=color_fg_set)
        
        plt.pause(0.001) #required



#Loop###################################################################
if PRINT_DEBUG:
    print("Starting loop")
    
if PRINT_PERFORMANCE:
    time_start = time.monotonic() #Create initial time_start var
    
while True:
    try:
        frame_array = get_frame()
        
        if test_pixels: #If pixels should be tested
            temp_alarm(not measurement_points(frame_array, test_array)) #Check if alarm nets to be activated
            
        if pixel_trigger: #If pixels in specified range should trigger a save
            autotrigger(frame_array)
            
        if save_queued: #save if queued
            save_now(save_queued_frame)
            if not SAVE_IMG:
                update_view(frame_array) #If image is not saved, the view still needs to be updated :)
        else:
            update_view(frame_array) #save_now() already updates view (only if SAVE_IMG).
                    
        if PRINT_CLEAR:
            os.system("clear")
        
        if PRINT_PERFORMANCE:
            time_stop = time.monotonic()
            frametime = time_stop - time_start
            print("Frametime: " + str(round(frametime, 1)) + " s")
            fps = 1 / frametime
            print("Framerate: " + str(round(fps, 1)) + " fps")
            time_start = time.monotonic()
        
        if OVERHEAT_DETECTION:
            temp_cpu_protect()
            
    except ValueError:
        if PRINT_VALUEERROR:
            print("ValueError")
             
        continue # if error, try again
