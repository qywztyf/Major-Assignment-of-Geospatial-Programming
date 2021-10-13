from qgis.core import *
from qgis import processing
from qgis.PyQt.QtCore import QVariant
import math
import datetime

start_t = datetime.datetime.now()

#put parameter
input_angle = 30
filepath = "/Users/liuhanyuan/Desktop/Major Program/"
filename = "DEM_test.tif"
savepath = "/Users/liuhanyuan/Desktop/Major Program/"
savename = "result.tif"

tan_angle = math.tan(input_angle * 3.1415926535 / 180)

#Checking whether the CRS of DEM data is in meters
layer = filepath + filename
ras = QgsRasterLayer(layer)
crs = ras.crs()
unit = crs.mapUnits()
if QgsUnitTypes.toString(unit) == "meters":
    print('Valid CRS, Unit is {}'.format(QgsUnitTypes.toString(unit)))
else:
    print('Invalid unit! Unit is {}, please convert CRS, such as UTM'.format(QgsUnitTypes.toString(unit)))
    raise AssertionError

start_t1 = datetime.datetime.now()

#calculate the maximum elevation of given DEM
Max = processing.run("qgis:rasterlayerstatistics",
    {
        'INPUT':filepath + filename,
        'BAND':1,
    }
)
max = Max['MAX']

#DEM to points
point = processing.run("qgis:pixelstopoints",
    {
        'INPUT_RASTER':filepath + filename,
        'RASTER_BAND':1,
        'FIELD_NAME':"ELEVATION",
        'OUTPUT':"memory:"
    }
)

#calculate the radius required to buffer each point
calculate = processing.run("qgis:fieldcalculator",
    {
        'INPUT':point['OUTPUT'],
        'FIELD_NAME':"Radius",
        'FIELD_TYPE':0,
        'FIELD_LENGTH':10,
        'FIELD_PRECISION':15,
        'NEW_FIELD':True,
        'FORMULA':'(max - "ELEVATION")/tan_angle',
        'OUTPUT':"memory:"
    }
)

#creating variable distance buffer by each radius above
point_buffer = processing.run("qgis:variabledistancebuffer",
    {
        'INPUT':point['OUTPUT'],
        'FIELD':"Radius",
        'SEGMENTS':5,
        'DISSOLVE': False,
        'END_CAP_STYLE':0,
        'JOIN_SYTLE':0,
        'MITER_LIMIT': 2,
        'OUTPUT': "memory:"
    }
)

#count the number of points that each point buffer has
count = processing.run("qgis:countpointsinpolygon",
    {
        'POLYGONS':point_buffer['OUTPUT'],
        'POINTS':point['OUTPUT'],
        'FIELD':'NUMPOINTS',
        'OUTPUT': "memory:"
    }
)

#statistic the first quartile, median, third quartile and Maximum of count
statistics_count = processing.run("qgis:basicstatisticsforfields",
    {
        'INPUT_LAYER':count['OUTPUT'],
        'FIELD_NAME':'NUMPOINTS',
    }
)

end_t1 = datetime.datetime.now()
start_t2 = datetime.datetime.now()

#join count result to point layer
point_count = processing.run("qgis:joinattributestable",
    {
        'INPUT':point['OUTPUT'],
        'FIELD':"ELEVATION",
        'INPUT_2':count['OUTPUT'],
        'FIELD_2':"ELEVATION",
        'METHOD':1,
        'DISCARD_NONMATCHING':"TRUE",
        'OUTPUT': 'memory:'
    }
)

#extract first quartile count point
point_count_1 = processing.run("qgis:extractbyattribute",
    {
        'INPUT':point_count['OUTPUT'],
        'FIELD':'NUMPOINTS',
        'OPERATOR':5,
        'VALUE':statistics_count['FIRSTQUARTILE'],
        'OUTPUT':"memory:",
        'FAIL_OUTPUT':"memory:"
    }
)

#extract median count point
point_count_2 = processing.run("qgis:extractbyattribute",
    {
        'INPUT':point_count_1['FAIL_OUTPUT'],
        'FIELD':'NUMPOINTS',
        'OPERATOR':5,
        'VALUE':statistics_count['MEDIAN'],
        'OUTPUT':"memory:",
        'FAIL_OUTPUT':"memory:"
    }
)

#extract third quartile and maximum count point
point_count_3 = processing.run("qgis:extractbyattribute",
    {
        'INPUT':point_count_2['FAIL_OUTPUT'],
        'FIELD':'NUMPOINTS',
        'OPERATOR':5,
        'VALUE':int(statistics_count['THIRDQUARTILE']),
        'OUTPUT':"memory:",
        'FAIL_OUTPUT':"memory:"
    }
)

#computing distance matrix as first quartile
distance_matrix_1 = processing.run("qgis:distancematrix",
    {
        'INPUT':point_count_1['OUTPUT'],
        'INPUT_FIELD':"ELEVATION",
        'TARGET':point['OUTPUT'],
        'TARGET_FIELD':"ELEVATION",
        'MATRIX_TYPE':0,
        'NEAREST_POINTS':statistics_count['FIRSTQUARTILE'],
        'OUTPUT': "memory:"
    }
)

#computing distance matrix as fmedian
distance_matrix_2 = processing.run("qgis:distancematrix",
    {
        'INPUT':point_count_2['OUTPUT'],
        'INPUT_FIELD':"ELEVATION",
        'TARGET':point['OUTPUT'],
        'TARGET_FIELD':"ELEVATION",
        'MATRIX_TYPE':0,
        'NEAREST_POINTS':statistics_count['MEDIAN'],
        'OUTPUT': "memory:"
    }
)

#computing distance matrix as third quartile
distance_matrix_3 = processing.run("qgis:distancematrix",
    {
        'INPUT':point_count_3['OUTPUT'],
        'INPUT_FIELD':"ELEVATION",
        'TARGET':point['OUTPUT'],
        'TARGET_FIELD':"ELEVATION",
        'MATRIX_TYPE':0,
        'NEAREST_POINTS':statistics_count['THIRDQUARTILE'],
        'OUTPUT': "memory:"
    }
)

#computing distance matrix as maximum
distance_matrix_4 = processing.run("qgis:distancematrix",
    {
        'INPUT':point_count_3['FAIL_OUTPUT'],
        'INPUT_FIELD':"ELEVATION",
        'TARGET':point['OUTPUT'],
        'TARGET_FIELD':"ELEVATION",
        'MATRIX_TYPE':0,
        'NEAREST_POINTS':statistics_count['MAX'],
        'OUTPUT': "memory:"
    }
)

#merge all distance matrix above
distance_matrix = processing.run("qgis:mergevectorlayers",
    {
        'LAYERS':[distance_matrix_1['OUTPUT'], distance_matrix_2['OUTPUT'], distance_matrix_3['OUTPUT'], distance_matrix_4['OUTPUT']],
        'OUTPUT': "memory:"
    }
)

#extract attribute by TargetID > InputID
distance_matrix_selected = processing.run("qgis:extractbyexpression",
    {
        'INPUT':distance_matrix['OUTPUT'],
        'EXPRESSION':'"TargetID" > "InputID"',
        'OUTPUT': "memory:"
    }
)

end_t2 = datetime.datetime.now()
start_t3 = datetime.datetime.now()

#calculating the elevation angle tangent of each point
angle = processing.run("qgis:fieldcalculator",
    {
        'INPUT':distance_matrix_selected['OUTPUT'],
        'FIELD_NAME':'Tangent',
        'FIELD_TYPE':0,
        'FIELD_LENGTH':10,
        'FIELD_PRECISION':15,
        'NEW_FIELD':True,
        'FORMULA':'("TargetID" - "InputID")/"Distance"',
        'OUTPUT':"memory:"
    }
)

#extract only elevation angle tangent > threshold tangent
threshold = processing.run("qgis:extractbyattribute",
    {
        'INPUT':angle['OUTPUT'],
        'FIELD':'Tangent',
        'OPERATOR':2,
        'VALUE':tan_angle,
        'OUTPUT':"memory:"
    }
)

end_t3 = datetime.datetime.now()
start_t4 = datetime.datetime.now()

#add the classified field with 0
classified = processing.run("qgis:fieldcalculator",
    {
        'INPUT':threshold['OUTPUT'],
        'FIELD_NAME':"Classified",
        'FIELD_TYPE':0,
        'FIELD_LENGTH':1,
        'FIELD_PRECISION':1,
        'NEW_FIELD':True,
        'FORMULA':'0',
        'OUTPUT':"memory:"
    }
)

#make a raster layer with 1 only
temp = processing.run("gdal:rastercalculator",
    {
        'INPUT_A':filepath + filename,
        'BAND_A':1,
        'FORMULA':'1',
        'RTYPE':5,
        'OUTPUT':savepath + savename
    }
)

#over all classified 0 to the raster layer and show it
result = processing.run("gdal:rasterize_over",
    {
        'INPUT':classified['OUTPUT'],
        'INPUT_RASTER':savepath + savename,
        'FIELD':"Classified",
        'ADD':"False",
    }
)
iface.addRasterLayer(result['OUTPUT'], "result")

end_t4 = datetime.datetime.now()
end_t = datetime.datetime.now()

elapsed_sec = (end_t - start_t).total_seconds()
elapsed_sec1 = (end_t1 - start_t1).total_seconds()
elapsed_sec2 = (end_t2 - start_t2).total_seconds()
elapsed_sec3 = (end_t3 - start_t3).total_seconds()
elapsed_sec4 = (end_t4 - start_t4).total_seconds()

print("Nearest points number of 4 distance matrix：" + format(statistics_count['FIRSTQUARTILE']) + ", " + format(statistics_count['MEDIAN']) + ", " + format(statistics_count['THIRDQUARTILE']) + ", " + format(statistics_count['MAX']))
print("Total time: " + "{:.2f}".format(elapsed_sec) + " seconds")
print("Buffer and counting points time: " + "{:.2f}".format(elapsed_sec1) + " seconds")
print("Distance matrix time: " + "{:.2f}".format(elapsed_sec2) + " seconds")
print("Calculating tangent time: " + "{:.2f}".format(elapsed_sec3) + " seconds")
print("Classification and rasterize time: " + "{:.2f}".format(elapsed_sec4) + " seconds")