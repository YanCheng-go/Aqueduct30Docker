
# coding: utf-8

# Goal is to create read / write functions for FeatureCollections to AWS RDS PostGreSQL 
# 
# 
# This script contains the following options:
# 
# * fc -> Geopandas 
# * Geopandas -> postGIS
# 
# * PostGIS -> GeoPandas 
# * GeoPandas -> fc
# 
# * fc -> pandas 
# * pandas -> postgreSQL 
# 
# * postgresql -> Pandas
# * Pandas -> fc
# 
# 
# 
# TODO:
# 
# laatste stap: Geopandas - > Fc heeft probelemen met Geometry in GeoJSON
# 
# 
# 

# In[3]:

get_ipython().magic('matplotlib inline')


# In[4]:

import ee
import pandas as pd
import geopandas as gpd

import folium
import folium_gee
import branca 

import shapely
import shapely.wkt

import boto3
import botocore
import sqlalchemy
import geoalchemy2
import geojson
import geojsonio

#from shapely.geometry.multipolygon import MultiPolygon
#from shapely.geometry import shape


# In[5]:

ee.Initialize()


# In[6]:

# Database settings
OUTPUT_VERSION= 1

DATABASE_IDENTIFIER = "aqueduct30v03"
DATABASE_NAME = "database01"
TABLE_NAME = "hydrobasin6_v%0.2d" %(OUTPUT_VERSION)


# In[81]:

def rdsConnect(database_identifier,database_name):
    """open a connection to AWS RDS
    
    in addition to specifying the arguments you need to store your password in a file called .password in the current working directory. 
    You can do this using the command line or Jupyter. Make sure to have your .gitignore file up to date.
    
    Args:
        database_identifier (string) : database identifier used when you set up the AWS RDS instance
        database_name (string) : the database name to connect to
        
    Returns:
        engine (sqlalchemy.engine.base.Engine) : database engine
        connection (sqlalchemy.engine.base.Connection) : database connection
    """
    
    
    rds = boto3.client('rds')
    F = open(".password","r")
    password = F.read().splitlines()[0]
    F.close()
    response = rds.describe_db_instances(DBInstanceIdentifier="%s"%(database_identifier))
    status = response["DBInstances"][0]["DBInstanceStatus"]
    print("Status:",status)
    endpoint = response["DBInstances"][0]["Endpoint"]["Address"]
    print("Endpoint:",endpoint)
    engine = sqlalchemy.create_engine('postgresql://rutgerhofste:%s@%s:5432/%s' %(password,endpoint,database_name))
    connection = engine.connect()
    return engine, connection


def fcToGdf(fc,crs = {'init' :'epsg:4326'}):
    """converts a featurecollection to a geoPandas GeoDataFrame. Use this function only if all features have a geometry.  
    
    caveats:
    Currently only supports non-geodesic (planar) geometries because of limitations in geoPandas and Leaflet. Geodesic geometries are simply interpreted as planar geometries. 
    FeatureCollections larger than memory are currently not supported. Consider splitting data and merging (server side) afterwards. 
    
    Args:
        fc (ee.FeatureCollection) : the earth engine feature collection to convert. 
        crs (dictionary, optional) : the coordinate reference system in geopandas format. Defaults to {'init' :'epsg:4326'}
        
    Returns:
        gdf (geoPandas.GeoDataFrame or pandas.DataFrame) : the corresponding (geo)dataframe. 
        
    """
    crs = {'init' :'epsg:4326'}
    
    features = fc.getInfo()['features']
    dictarr = []

    for f in features:
        #geodesic = ee.Feature(f).geometry().edgesAreGeodesics()
        #if geodesic:
        attr = f['properties']
        attr['geometry'] = f['geometry']
        attr['geometry']
        dictarr.append(attr)

    gdf = gpd.GeoDataFrame(dictarr)
    gdf['geometry'] = map(lambda s: shapely.geometry.shape(s), gdf.geometry)
    gdf.crs = crs
    return gdf

def fcToDf(fc):
    """converts a featurecollection to a Pandas DataFrame. Use this function for featureCollections without geometries. For featureCollections with geometries, use fcToGdf()
    
    Args:
        fc (ee.FeatureCollection) : the earth engine feature collection to convert. Size is limited to memory (geopandas limitation)
        crs (dictionary, optional) : the coordinate reference system in geopandas format. Defaults to {'init' :'epsg:4326'}
        
    Returns:
        df (pandas.DataFrame) : the corresponding dataframe. 
        
    """
    
    features = fc.getInfo()['features']
    dictarr = []    
    for f in features:
        attr = f['properties']
        dictarr.append(attr)
    
    df = pd.DataFrame(dictarr)
    return df

def gdfToPostGIS(connection, gdf,tableName,saveIndex = True):
    """this function uploads a geodataframe to table in AWS RDS.
    
    It handles combined polygon/multipolygon geometry and stores it in valid multipolygon in epsg 4326.
    
    Args:
        connection (sqlalchemy.engine.base.Connection) : postGIS enabled database connection 
        gdf (geoPandas.GeoDataFrame) : input geoDataFrame
        tableName (string) : postGIS table name (string)
        saveIndex (boolean, optional) : save geoDataFrame index column in separate column in postgresql, otherwise discarded. Default is True
        
    Returns:
        gdf (geoPandas.GeoDataFrame) : the geodataframe loaded from the database. Should match the input dataframe
    
    todo:
        currently removes table if exists. Include option to break or append
    
    """   
    
    gdf["type"] = gdf.geometry.geom_type    
    geomTypes = ["Polygon","MultiPolygon"]
    
    for geomType in geomTypes:
        gdfType = gdf.loc[gdf["type"]== geomType]
        geomTypeLower = str.lower(geomType)
        gdfType['geom'] = gdfType['geometry'].apply(lambda x: geoalchemy2.WKTElement(x.wkt, srid=4326))
        gdfType.drop(["geometry","type"],1, inplace=True)      
        print("Create table temp%s" %(geomTypeLower)) 
        gdfType.to_sql(
            name = "temp%s" %(geomTypeLower),
            con = engine,
            if_exists='replace',
            index= saveIndex, 
            dtype={'geom': geoalchemy2.Geometry(str.upper(geomType), srid= 4326)}
        )
        
    # Merge both tables and make valid
    sql = []
    sql.append("DROP TABLE IF EXISTS %s"  %(tableName))
    sql.append("ALTER TABLE temppolygon ALTER COLUMN geom type geometry(MultiPolygon, 4326) using ST_Multi(geom);")
    sql.append("CREATE TABLE %s AS (SELECT * FROM temppolygon UNION SELECT * FROM tempmultipolygon);" %(tableName))
    sql.append("UPDATE %s SET geom = st_makevalid(geom);" %(tableName))
    sql.append("DROP TABLE temppolygon,tempmultipolygon")

    for statement in sql:
        print(statement)
        result = connection.execute(statement)    
    gdfFromSQL =gpd.GeoDataFrame.from_postgis("select * from %s" %(tableName),connection,geom_col='geom' )
    return gdfFromSQL


def dfToPostgreSQL(connection, df,tableName,saveIndex = True):
    """this function uploads a dataframe to table in AWS RDS.
       
    Args:
        connection (sqlalchemy.engine.base.Connection) :database connection 
        df (pandas.GeoDataFrame) : input dataFrame
        tableName (string) : table name (string)
        saveIndex (boolean, optional) : save geoDataFrame index column in separate column in postgresql, otherwise discarded. Default is True
        
    Returns:
        gdf (geoPandas.GeoDataFrame) : the geodataframe loaded from the database. Should match the input dataframe
    
    todo:
        currently removes table if exists. Include option to break or append
    
    """  
    df.to_sql(
        name = tableName,
        con = connection,
        if_exists="replace",
        index = saveIndex,
        chunkSize = None
    )

    return 1


def postGisToGdf(connection,tableName):
    """this function gets a geoDataFrame from a postGIS database instance
    
    
    Args:
        connection (sqlalchemy.engine.base.Connection) : postGIS enabled database connection 
        tableName (string) : table name
 
    Returns:
        gdf (geoPandas.GeoDataFrame) : the geodataframe from PostGIS
        
    todo:
        allow for SQL filtering
    
    
    """   
    gdf =gpd.GeoDataFrame.from_postgis("select * from %s" %(tableName),connection,geom_col='geom' )
    gdf.crs =  {'init' :'epsg:4326'}
    return gdf

def postgreSQLToDf(connection,tableName):
    """this function gets a dataFrame from a postGIS database instance
    
    Args:
        connection (sqlalchemy.engine.base.Connection) : postGIS enabled database connection 
        tableName (string) : table name
 
    Returns:
        df (pandas.DataFrame) : the dataframe from PostGIS
        
    todo:
        allow for SQL filtering
    
    
    """   
    df = pd.read_sql_query('select * from "%s"' %(tableName),con=engine )
    return df


def shapelyToEEFeature(row):
    properties = row.drop(["geometry"]).to_dict()
    geoJSONfeature = geojson.Feature(geometry=row["geometry"], properties=properties)
    return ee.Feature(geoJSONfeature)

def noGeometryEEFeature(row):
    properties = row.to_dict()
    return ee.Feature(None,properties)
    
    
def gdfToFc(gdf):
    """converts a geodataframe  to a featurecollection
    
    Args:
        gdf (geoPandas.GeoDataFrame) : the input geodataframe
        
    Returns:
        fc (ee.FeatureCollection) : feature collection (server side)  
    
    
    """
    gdfCopy = gdf.copy()
    gdfCopy["eeFeature"] = gdfCopy.apply(shapelyToEEFeature,1)
    featureList = gdfCopy["eeFeature"].tolist()
    fc =  ee.FeatureCollection(featureList)
    return fc


def dfToFc(df):
    """converts a dataframe  to a featurecollection without geometry
    
    Args:
        df (pandas.dataFrame) : the input dataframe
        
    Returns:
        fc (ee.FeatureCollection) : feature collection with empty geometry
    
    
    """
    dfCopy = df.copy()
    dfCopy["eeFeature"] = gdfCopy.apply(noGeometryEEFeature,1)
    featureList = dfCopy["eeFeature"].tolist()
    fc =  ee.FeatureCollection(featureList)
    return fc
    

def shapelyToFoliumFeature(row):
    """converts a shapely feature to a folium (leaflet) feature. row needs to have a geometry column. CRS is 4326
    
    Args:
        row (geoPandas.GeoDataFrame row) : the input geodataframe row. Appy this function to a geodataframe gdf.appy(function, 1)
        
    Returns:
        foliumFeature  (folium feature) : foliumFeature with popup child.
    
    """    

    width, height = 310,110
    dfTemp = pd.DataFrame(row.drop("geometry"))
    htmlTable = dfTemp.to_html()
    iFrame = branca.element.IFrame(htmlTable, width=width, height=height)
    geoJSONfeature = geojson.Feature(geometry=row["geometry"], properties={})
    foliumFeature = folium.features.GeoJson(geoJSONfeature)
    foliumFeature.add_child(folium.Popup(iFrame))
    return foliumFeature 
    

    
def defaultMap():
    m = folium.Map(
        location=[5, 52],
        tiles='Mapbox Bright',
        zoom_start=4
    )
    return m


def gdfToFoliumGroup(gdf,name="noName",m=None):
    """converts a geodataframe  to a folium featureGroup with the properties as a popup child
    
    Args:
        gdf (geoPandas.GeoDataFrame) : the input geodataframe
        name (string) : output folium feature group name
        
    Returns:
        fc (ee.FeatureCollection) : feature collection (server side)  
    """
     
    featureGroup = folium.FeatureGroup(name=name)
    if m:
        pass
    else:
        m = defaultMap()
    
    features = gdf.apply(shapelyToFoliumFeature,1)   
    map(lambda x: x.add_to(featureGroup),features)
        
    return featureGroup



def eeImageToFoliumLayer(image,layerName="eeLayer",vis_params=None,folium_kwargs={}):
    """
    Function to add Google Earch Engine tile layer as a Folium layer.
    based on https://github.com/mccarthyryanc/folium_gee/blob/master/folium_gee.py
    
    Args:
        image (ee.Image) : Google Earth Engine Image.
        layerName (string) : Layer name for in folium layerControl. Default : "eeLayer"
        vis_params (dict) : Dict with visualization parameters as used in Google Earth Engine. Note that color palatte inputs in python needs to be structured like: "palette": "ff0000,ff0000,0013ff"
        folium_kwargs (dict) : Keyword args for Folium Map.
        
    Returns:
        layer () : folium Layer. Add to map by applying method .add(m)
        
    """
    
    # Get the MapID and Token after applying parameters
    image_info = image.getMapId(vis_params)
    mapid = image_info['mapid']
    token = image_info['token']
    folium_kwargs['attr'] = ('Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a> ')
    folium_kwargs['tiles'] = "https://earthengine.googleapis.com/map/%s/{z}/{x}/{y}?token=%s"%(mapid,token)
    
    layer = folium.TileLayer(**folium_kwargs)
    layer.layer_name = "test"
    return layer


# # Testing

# * fc -> Geopandas   
# * Geopandas -> postGIS
# 
# * PostGIS -> GeoPandas 
# * GeoPandas -> fc
# 
# * fc -> pandas  
# * pandas -> postgreSQL 
# 
# * postgresql -> Pandas
# * Pandas -> fc
# 

# In[82]:

image = ee.Image("projects/WRI-Aquaduct/PCRGlobWB20V07/accumulateddrainagearea_05min_km2")


# In[83]:

visParam =  {"opacity":1,"min":-52190.75236876079,"max":67316.43600722033,"palette":'ff0000,0013ff'}


# In[84]:

print(visParam)


# In[85]:

test = image.getMapId(visParam)


# In[ ]:




# In[89]:

visParam =  {"opacity":0.4,"min":-52190.75236876079,"max":67316.43600722033,"palette": "ff0000,ff0000,0013ff"}


# In[90]:

layer = eeImageToFoliumLayer(image,visParam,folium_kwargs={})


# In[98]:

FeatureGroup = gdfToFoliumGroup(gdf)


# In[99]:

m = defaultMap()
layer.add_to(m)
FeatureGroup.add_to(m)
folium.LayerControl().add_to(m)
m


# In[ ]:




# In[27]:

engine, connection = rdsConnect(DATABASE_IDENTIFIER,DATABASE_NAME)


# In[28]:

fc = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017");
fcEu = fc.filter(ee.Filter.eq("wld_rgn","Europe"))
fcTest = fcEu.filter(ee.Filter.inList("country_co",["PO","NL"]))


# In[97]:

gdf = fcToGdf(fcTest)


# In[30]:

gdf


# In[11]:

fcNoGeom = ee.FeatureCollection("ft:1LAkQiS-bB71VbzRG6jKPKCO6mQj3fKjLR2RD-68K")


# In[12]:

df =fcToDf(fcNoGeom)


# In[13]:

df


# In[ ]:




# In[ ]:

geometry = ee.Geometry.Polygon(coords=[[-180.0, -90.0], [180,  -90.0], [180, 90], [-180,90]], proj= ee.Projection('EPSG:4326'),geodesic=False )


# In[ ]:

geometry2 = ee.Geometry.Polygon(coords=[[-180.0, -90.0], [180,  -90.0], [180, 90], [-180,90]], proj= ee.Projection('EPSG:4326'),geodesic=True )


# In[ ]:




# In[22]:

geometry3 = ee.Geometry.Polygon(coords=[[-170.0, -80.0], [170,  -80.0], [170, 80], [-170,80]], proj= ee.Projection('EPSG:4326'),geodesic=True )


# In[23]:

feature = ee.Feature(geometry3,{})


# In[24]:

geoJSON = feature.geometry().getInfo()


# In[25]:

print(geoJSON)


# In[18]:

geoJSON["geodesic"] = False


# In[19]:

print(geoJSON)


# In[20]:

feature = ee.Feature(geoJSON)


# In[21]:

print(feature.getInfo())


# In[ ]:

fc = ee.FeatureCollection([feature])


# In[ ]:

gdf = fcToGdf(fc)


# In[ ]:

test = gdf.to_json()


# In[ ]:

print(test)


# In[ ]:




# In[ ]:

featureGroup = gdfToFoliumGroup(gdf)


# In[37]:

m = defaultMap()
#featureGroup.add_to(m)
m


# In[38]:

type(m)


# In[ ]:

gdf1 = fcToGdf(fc1)
gdf2 = fcToGdf(fc2)


# In[ ]:

geoJSONfeature = geojson.Feature(geoJSONstring, properties={})


# In[ ]:

type(geoJSONfeature)


# In[ ]:

foliumFeature = folium.features.GeoJson(geoJSONfeature)


# In[ ]:

m = defaultMap()
foliumFeature.add_to(m)
m


# In[ ]:




# In[ ]:




# In[ ]:

group1 = gdfToFoliumGroup(gdf1)


# In[ ]:

group2 = gdfToFoliumGroup(gdf2)


# In[ ]:




# In[ ]:




# In[ ]:




# Plot GDF on folium map with popups

# In[ ]:

test = gdfToFoliumGroup(gdf)


# In[ ]:

m = defaultMap()
featureGroup.add_to(m)
m

