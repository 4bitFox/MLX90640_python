# MLX90640_python
![THC_2022-05-05_07-33-24](https://raw.githubusercontent.com/4bitFox/MLX90640_python/main/saves/default/THC_2022-05-05_07-33-24.png)

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


Sometimes, the script assumes, that you put the files into "/home/pi/thcam". If you put them in a different place, you might need to change some paths. Shouldn't be too hard :-)

Modules required (pip3 install):
- adafruit-circuitpython-mlx90640
- adafruit-blinka
- RPi.GPIO
- numpy
- matplotlib
- configparser

The viever only requires:
- numpy
- matplotlib
- configparser

Version of Python used:
- Python 3.9.2
- Python 3.10

Versions of modules used:
- adafruit-circuitpython-mlx90640   1.2.9
- adafruit-blinka                   8.0.2
- RPi.GPIO                          0.7.1
- numpy                             1.22.4
- matplotlib                        3.5.2
- configparser                      5.2.0
