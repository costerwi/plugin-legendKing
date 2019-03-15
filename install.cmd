@echo off

set plugin=legendScale
set destination=%USERPROFILE%\abaqus_plugins

echo This script installs the Abaqus plugin "%plugin%" in "%destination%"

if not exist "%destination%" (
    echo ERROR: "%destination%" does not exist.
    pause
    exit 1
)

set destination=%destination%\%plugin%
if not exist "%destination%" mkdir "%destination%"
copy *.py "%destination%"
if ERRORLEVEL 0 (
    echo Success! Restart Abaqus CAE and check Plugin-ins menu.
) else (
    echo Something went wrong. Contact osterwisch@caelynx.com
)
pause
