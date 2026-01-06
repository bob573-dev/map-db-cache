$Root = "C:\Users\pajyloy\AppData\Local\Programs\OSGeo4W"


$OutDir  = "gdal_win"
$BinDir  = "$OutDir\bin"
$DataDir = "$OutDir\data"
$PlugDir = "$OutDir\plugins"
$PyDir   = "$OutDir\python"
$UtilsDir = "$PyDir\osgeo_utils"

$GdalRepoRaw = "https://raw.githubusercontent.com/OSGeo/gdal/master/swig/python/gdal-utils/osgeo_utils"

Remove-Item -Recurse -Force $OutDir -ErrorAction Ignore
New-Item -ItemType Directory -Force `
    -Path $BinDir, $DataDir, $PlugDir, $PyDir, $UtilsDir | Out-Null

# ----------------------------
# GDAL / OGR executables
# ----------------------------
$Executables = @(
    "gdal_translate.exe",
    "gdalbuildvrt.exe",
    "gdalwarp.exe",
    "gdaldem.exe",
    "gdal_contour.exe",
    "gdal_rasterize.exe",
    "ogr2ogr.exe"
)

Write-Host "Copying GDAL/OGR executables..."
foreach ($exe in $Executables) {
    Copy-Item "$Root\bin\$exe" $BinDir -ErrorAction Stop
}


# ----------------------------
# DLL dependencies
# ----------------------------
Write-Host "Copying DLL dependencies..."
Copy-Item "$Root\bin\*.dll" $BinDir -ErrorAction Stop

# ----------------------------
# GDAL data files
# ----------------------------
Write-Host "Copying GDAL data..."
Copy-Item "$Root\apps\gdal\share\gdal" "$DataDir\gdal" -Recurse -ErrorAction Stop

# ----------------------------
# PROJ data files
# ----------------------------
Write-Host "Copying PROJ data..."
Copy-Item "$Root\share\proj" "$DataDir\proj" -Recurse -ErrorAction Stop

# ----------------------------
# GDAL plugins
# ----------------------------
Write-Host "Copying GDAL plugins..."
Copy-Item "$Root\apps\gdal\lib\gdalplugins" "$PlugDir\gdal" -Recurse -ErrorAction Stop

# ----------------------------
# Download Python GDAL utilities from GitHub
# ----------------------------
Write-Host "Downloading gdal Python utilities from GDAL repo..."

$PythonUtils = @(
    "gdal2tiles.py",
    "gdal_calc.py",
    "__init__.py"
)

foreach ($file in $PythonUtils) {
    $url = "$GdalRepoRaw/$file"
    $out = "$UtilsDir\$file"

    Write-Host "  - $file"
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -ErrorAction Stop
}


Write-Host ""
Write-Host "GDAL Windows bundle built successfully → $OutDir"
