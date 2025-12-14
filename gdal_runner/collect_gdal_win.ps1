$Root = "C:\Users\user\AppData\Local\Programs\OSGeo4W"


$OutDir  = "gdal_win"
$BinDir  = "$OutDir\bin"
$DataDir = "$OutDir\data"
$PlugDir = "$OutDir\plugins"

Remove-Item -Recurse -Force $OutDir -ErrorAction Ignore
New-Item -ItemType Directory -Force `
    -Path $BinDir, $DataDir, $PlugDir | Out-Null

Write-Host "Copying GDAL executables..."
Copy-Item "$Root\bin\gdal_translate.exe" $BinDir
Copy-Item "$Root\bin\gdalbuildvrt.exe" $BinDir

Write-Host "Copying DLL dependencies..."
Copy-Item "$Root\bin\*.dll" $BinDir

Write-Host "Copying GDAL data..."
Copy-Item "$Root\apps\gdal\share\gdal" "$DataDir\gdal" -Recurse

Write-Host "Copying PROJ data..."
Copy-Item "$Root\share\proj" "$DataDir\proj" -Recurse

Write-Host "Copying GDAL plugins..."
Copy-Item "$Root\apps\gdal\lib\gdalplugins" "$PlugDir\gdal" -Recurse

Write-Host "GDAL Windows bundle built → $OutDir"
