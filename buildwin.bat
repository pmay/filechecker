::::::::::::::::::::::::::::::::::
:: Script to build FileChecker exe ::
::::::::::::::::::::::::::::::::::

@echo off
SETLOCAL

IF EXIST .\venv_32\ ( CALL :Build 32 ) ELSE ( echo "Requires virtual environment (named venv_32) with pyinstall" )
IF EXIST .\venv_64\ ( CALL :Build 64 ) ELSE ( echo "Requires virtual environment (named venv_64) with pyinstall" )
EXIT /B %ERRORLEVEL%
:::::::::::::::::::::::::::::::::::::::::

:Build
  SET bitness=%~1
  echo Building %bitness%-bit FileChecker
  :: switch to correct bitness venv
  CALL venv_%bitness%\Scripts\activate.bat

  :: run pyinstaller to build
  pyinstaller --workpath=build\pyi.win%bitness% --distpath=dist\win%bitness% -y filechecker-onefile.spec

  :: switch back out of venv  
  CALL venv_%bitness%\Scripts\deactivate.bat
  echo Finished building %bitness%-bit FileChecker
  echo.
  EXIT /B 0

:End
