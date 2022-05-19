# MLX90640_python

![THC_2022-05-05_07-33-24](https://user-images.githubusercontent.com/33175205/169257910-2e832b41-b9c4-45d0-9cfe-f5537ee1db31.png)


Inherited initial code from here:
https://makersportal.com/blog/2020/6/8/high-resolution-thermal-camera-with-raspberry-pi-and-mlx90640
Code now:
https://github.com/4bitFox/MLX90640_python/blob/main/thcam.py

Features:
- Load settings from config file 
  - https://github.com/4bitFox/MLX90640_python/blob/main/configs/default.ini
  - Generate new config file:
    - https://github.com/4bitFox/MLX90640_python/blob/main/conf_new.py
- Set a temperature range to display. Ignore the rest.
- Monitor specific pixels.
  - Display turns red if temperatures are not in the tolerance.
  - Sound a buzzer
- Interpolation of image
