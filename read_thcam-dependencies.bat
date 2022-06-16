@echo off 

echo PLEASE INSTALL THE NEWEST VERSION OF PYTHON 3 FROM THE MICROSOFT STORE.
echo I will open the Store for you in 15 seconds. :-)
timeout /T 15
explorer "ms-windows-store://publisher/?name=Python Software Foundation"

echo ------------------------------------------------------------
echo When you have installed Python 3, you can continue...
pause

echo ------------------------------------------------------------
echo I will now install the required Python libraries for you:
echo matplotlib configparser numpy
echo ...
pip3 install --upgrade pip
pip3 install matplotlib configparser numpy

echo ------------------------------------------------------------
echo All done.
echo You can open ".thcam" files with "read_thcam.bat".
echo You have to enter the correct "cd" path into "read_thcam.bat" for it to work!
echo The first time, you will have to use "open with" and point to "read_thcam.bat". 
echo While you are at it, feel free to check the "always open with" checkbox.
timeout /T 60
