@echo off
:: Start a new tab in Windows terminal with title 'Rebel placer' in current folder with command 'py rebel_placer.py'
wt --title "Rebel placer" -d "%cd%" powershell -NoExit -Command "py rebel_placer.py"
:: For index in range(2, 100) - index is referred to with %%G
FOR /L %%G IN (2, 1, 100) DO (
    :: If '2.ini' exists start a windows terminal tab with command 'py secondary_placer.py 2'
    if exist "%%G.ini" (
        timeout /t 20
        wt --title "Placer %%G" -d "%cd%" powershell -NoExit -Command "py secondary_placer.py %%G"
        )
    )
:: timeout /t 10
:: wt nt --title "Disconnect" -d "%cd%"