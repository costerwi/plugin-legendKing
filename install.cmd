@echo off

set plugin=legendScale

if defined HOME (
    set abaqus_plugins=%HOME%\abaqus_plugins
) else (
    set abaqus_plugins=%HOMEDRIVE%%HOMEPATH%\abaqus_plugins
)

echo This script copies the Abaqus CAE plugin "%plugin%" into "%abaqus_plugins%"

if not exist "%abaqus_plugins%" (
    echo ERROR: "%abaqus_plugins%" does not exist.
    pause
    exit 1
)

set destination=%abaqus_plugins%\%plugin%\
if "%~dp0"=="%destination%" (
    echo ERROR: Cannot install from destination directory.
    pause
    exit 1
)

if not exist "%destination%" mkdir "%destination%"
copy /Y *.* "%destination%"
if ERRORLEVEL 0 (
    echo Success! Restart Abaqus CAE and check Plugin-ins menu.
) else (
    echo Something went wrong. Contact support@caelynx.com
)
pause
