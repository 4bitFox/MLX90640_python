# MLX90640_python
![THC_2022-05-05_07-33-24](https://user-images.githubusercontent.com/33175205/169257910-2e832b41-b9c4-45d0-9cfe-f5537ee1db31.png)

Can be used as a thermal imager or even for monitoring.


Inherited initial code from Justin Lam:
https://gist.github.com/justinmklam/090d92011c6b7c9510f86b4cb667be92

Features:
- Save picture
  - Image
  - .thcam Raw file. Can be opened with read_thcam.py
- Load settings from config file
  - https://github.com/4bitFox/MLX90640_python/blob/main/configs/default.ini
  - Generate new config file:
    - https://github.com/4bitFox/MLX90640_python/blob/main/conf_new.py
- Set a temperature range to display. Ignore the rest.
- Monitor specific pixels.
  - Display turns red if temperatures are not in the tolerance.
  - Sound a buzzer
- Interpolation of image
- Alarm and automatic poweroff when Raspberry Pi overheats
- Takes pictures automatically, if all specified pixels are in tolerance.
  - Save a picture from X frames ago.


Modules required (pip3 install):
- adafruit-circuitpython-mlx90640
- adafruit-blinka
- RPI.GPIO
- numpy
- matplotlib
- configparser

The viever only requires:
- numpy
- matplotlib
- configparser


Versions of modules used:
- adafruit-circuitpython-mlx90640   1.2.9
- adafruit-blinka                   8.0.2
- RPi.GPIO                          0.7.1
- numpy                             1.22.4
- matplotlib                        3.5.2
- configparser                      5.2.0
