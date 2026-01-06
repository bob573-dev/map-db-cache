@echo off
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
python -u "%OSGEO4W_ROOT%\apps\Python312\Scripts\gdalcompare.py" %*
