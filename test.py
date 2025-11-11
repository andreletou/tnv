from osgeo import gdal, ogr

# Test des drivers raster
print("Drivers raster disponibles:")
for i in range(gdal.GetDriverCount()):
    driver = gdal.GetDriver(i)
    print(f"  - {driver.ShortName}: {driver.LongName}")

# Test des drivers vectoriels
print("\nDrivers vectoriels disponibles:")
for i in range(ogr.GetDriverCount()):
    driver = ogr.GetDriver(i)
    print(f"  - {driver.GetName()}")