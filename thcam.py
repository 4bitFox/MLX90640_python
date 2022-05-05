#!/bin/python3
import time,board,busio
import numpy as np
import adafruit_mlx90640
import matplotlib.backend_managers as bmg
import matplotlib.pyplot as plt
import datetime
import keyboard
import os



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
interpolation = "kaiser" #none, nearest, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos

SAVE_PREFIX = "THC_"
SAVE_SUFFIX = ""
SAVE_FILEFORMAT = "png"

PRINT_FPS = True
PRINT_SAVE = True



#Init MLX
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000) #I2C
mlx = adafruit_mlx90640.MLX90640(i2c) #MLX90640
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ #1, 2, 4, 8, 16, 32, 64 HZ possible
MLX_SHAPE = (24, 32) #MLX resolution



#Matplotlib
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
cbar.set_label('Temperature [$^{\circ}$C]', fontsize=14, color=color_fg) #Label
plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color=color_fg) #Tick labels



frame = np.zeros((24*32, )) #setup array for storing all 768 temperatures
t_array = []



def datetime():
    dt = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    return dt

def save():
    filename = SAVE_PREFIX + datetime() + SAVE_SUFFIX + "." + SAVE_FILEFORMAT
    fig.savefig(filename)
    if PRINT_SAVE:
        print(filename)



def loop():
    print("Starting loop")
    
    while True:
        t1 = time.monotonic()
        
        try:
            mlx.getFrame(frame) #read MLX temperatures into frame var
            data_array = (np.reshape(frame, MLX_SHAPE)) #reshape to 24x32
            therm1.set_data(np.fliplr(data_array)) #flip left to right
            therm1.set_clim(vmin=np.min(data_array), vmax=np.max(data_array)) #set bounds
            cbar.update_normal(therm1) #update colorbar range
            plt.title(f"Max Temp: {np.max(data_array):.1f} °C", color=color_fg)
            plt.pause(0.001) #required
            t_array.append(time.monotonic()-t1)
            
            if PRINT_FPS:
                #os.system("clear")
                print('Sample Rate: {0:2.1f}fps'.format(len(t_array)/np.sum(t_array)))
                
        except ValueError:
            continue # if error, just read again



loop()
