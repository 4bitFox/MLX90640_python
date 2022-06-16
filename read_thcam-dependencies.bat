@echo off 

echo BITTE INSTALLIEREN SIE DIE NEUSTE VERSION VON "PYTHON 3" AUS DEM MICROSOFT STORE.
echo Ich oeffne in 15 Sekunden den Store fuer Sie. :-)
timeout /T 15
explorer "ms-windows-store://publisher/?name=Python Software Foundation"

echo ------------------------------------------------------------
echo Wenn Sie Python 3 installiert haben, duerfen Sie fortfahren.
pause

echo ------------------------------------------------------------
echo Ich installiere nun die noetigen Python Bibliotheken:
echo matplotlib configparser numpy
echo ...
pip3 install --upgrade pip
pip3 install matplotlib configparser numpy

echo ------------------------------------------------------------
echo Alles erledigt.
echo Du kannst nun ".thcam" Dateien mit "read_thcam.bat" oeffnen.
echo Beim ersten mal muessen Sie die ".thcam" Dateien mit "Oeffnen mit" ausfuehren. Verweisen Sie dabei auf "read_thcam.bat".
timeout /T 60
