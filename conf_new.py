#!/bin/python3
import configparser
import sys


config_file_name = sys.argv[1]
#config_file_name = "default"
config_file_path = "/home/pi/thcam/configs"
config_file_format = "ini"


#Create Object
config_file = configparser.ConfigParser()


config_file.add_section("Accuracy")
config_file.set("Accuracy", "emissivity", "0.95")


config_file.add_section("Temperature_Range")
config_file.set("Temperature_Range", "range_enable", "False")
config_file.set("Temperature_Range", "range_min", "-40")
config_file.set("Temperature_Range", "range_max", "300")


config_file.add_section("Monitor")
config_file.set("Monitor", "monitor_pixels", "False")


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
