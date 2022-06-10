#!/bin/python3
import configparser
import sys

try:
    config_file_name = sys.argv[1]
except IndexError:
    print("Missing argument: No name specified!")
    print("Useage: python3 conf_new.py examplename")
    print("                            ^^^^^^^^^^^")
    sys.exit(1)


#config_file_name = "default"
config_file_path = "/home/pi/thcam/configs"
config_file_format = "ini"


#Create Object
config_file = configparser.ConfigParser()


config_file.add_section("View")
config_file.set("View", "interpolation", "gaussian #none, nearest, bilinear, bicubic, spline16, spline36, hanning, hamming, hermite, kaiser, quadric, catrom, gaussian, bessel, mitchell, sinc, lanczos")


config_file.add_section("Accuracy")
config_file.set("Accuracy", "emissivity", "0.95")


config_file.add_section("Temperature_Range")
config_file.set("Temperature_Range", "range_enable", "False")
config_file.set("Temperature_Range", "range_min", "-40")
config_file.set("Temperature_Range", "range_max", "300")


config_file.add_section("Monitor")
config_file.set("Monitor", "monitor_pixels_enable", "False #Monitor pixels, if they are in tolerance. If not, turn screen red.")
config_file.set("Monitor", "monitor_buzzer_enable", "True #Buzz once if monitored pixels are not in temperature tolerance.")
config_file.set("Monitor", "monitor_pixels_array", "[[0, 0, 20, 50], [0, 31, 30, 40], [23, 0, 10, 20], [23, 31, -10, 0], [11, 15, -40, 300]] #[[pos_y, pos_x, min_°C, max_°C], [...], ...]")
config_file.set("Monitor", "monitor_autotrigger_enable", "False #A picture will be taken, if all pixels of 'monitor_autotrigger_array' are in temperature tolerance.")
config_file.set("Monitor", "monitor_autotrigger_previous_frame", "5 #If a picture should automatically be taken, store a previous frame. For the current frame, set to '0'.")
config_file.set("Monitor", "monitor_autotrigger_array", "[[0, 0, 10, 50], [0, 31, 10, 50], [23, 0, 35, 50], [23, 31, 10, 50], [11, 15, 10, 50]] #[[pos_y, pos_x, min_°C, max_°C], [...], ...]")

config_file.add_section("Save")
config_file.set("Save", "save_path", "/home/pi/thcam/saves/default")
config_file.set("Save", "save_format", "png")
config_file.set("Save", "save_prefix", "THC_")
config_file.set("Save", "save_suffix", "")


#Save file
config_file_save = config_file_path + "/" + config_file_name + "." + config_file_format
with open(config_file_save, "w") as configfileObj:
    config_file.write(configfileObj)
    configfileObj.flush()
    configfileObj.close()
