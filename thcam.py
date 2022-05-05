#!/bin/python3
import time,board,busio
import numpy as np
import adafruit_mlx90640
import matplotlib.backend_managers as bmg
import matplotlib.pyplot as plt
import keyboard
import os

TITLE = "Thermal Camera"
SCREEN_W = 800
SCREEN_H = 480
interpolation = "kaiser" #none, nearest, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos
print_fps=True


print("Initializing MLX90640")
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000) #setup I2C
mlx = adafruit_mlx90640.MLX90640(i2c) #begin MLX90640 with I2C comm
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ #1, 2, 4, 8, 16, 32, 64 HZ
mlx_shape = (24, 32)
print("Initialized")

#setup the figure for plotting
plt.ion() #enables interactive plotting
fig,ax = plt.subplots(figsize=(12, 7))
#therm1 = ax.imshow(np.zeros(mlx_shape), vmin=0, vmax=60) #start plot with zeros
therm1 = ax.imshow(np.zeros(mlx_shape), vmin=0, vmax=60, interpolation=interpolation) #start plot with zeros
cbar = fig.colorbar(therm1) #setup colorbar for temps
cbar.set_label('Temperature [$^{\circ}$C]', fontsize=14) #colorbar label

fig.canvas.manager.set_window_title(TITLE)
fig.canvas.manager.window.move(0, -16)
fig.canvas.manager.window.resize(SCREEN_W, SCREEN_H)
#fig.canvas.manager.full_screen_toggle()

frame = np.zeros((24*32, )) #setup array for storing all 768 temperatures
t_array = []


#def close():
#    print("Quit")
#    plt.close("all")
#    sys.exit(0)

def loop():
    print("Starting loop")
    while True:
        t1 = time.monotonic()
        try:
            mlx.getFrame(frame) #read MLX temperatures into frame var
            data_array = (np.reshape(frame, mlx_shape)) #reshape to 24x32
            therm1.set_data(np.fliplr(data_array)) #flip left to right
            therm1.set_clim(vmin=np.min(data_array), vmax=np.max(data_array)) #set bounds
            cbar.update_normal(therm1) #update colorbar range
            plt.title(f"Max Temp: {np.max(data_array):.1f}C")
            plt.pause(0.001) #required
            #fig.savefig('mlx90640_test_fliplr.png',dpi=300,facecolor='#FCFCFC', bbox_inches='tight') #comment out to speed up
            t_array.append(time.monotonic()-t1)
            if print_fps:
                #os.system("clear")
                print('Sample Rate: {0:2.1f}fps'.format(len(t_array)/np.sum(t_array)))
#            if keyboard.is_pressed("q"):
#                close()
        except ValueError:
            continue # if error, just read again

loop()
