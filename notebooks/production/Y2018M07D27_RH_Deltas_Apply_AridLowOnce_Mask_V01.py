
# coding: utf-8

# In[1]:

""" Apply the mask for arid and lowwater use subbasins based on ols_ols10 (once) for deltas.
-------------------------------------------------------------------------------

Y2020M02D06 update output version 2-3 update input left 2-3, right 2-3

Join the results of the arid and lowwater use mask based on annual values (ols)
(ols_ols10_**) and the master table. 

The script uses the 2014 value for the right table. 


Author: Rutger Hofste
Date: 20180727
Kernel: python35
Docker: rutgerhofste/gisdocker:ubuntu16.04

Args:
    TESTING (Boolean) : Toggle testing case.
    SCRIPT_NAME (string) : Script name.
    OUTPUT_VERSION (integer) : output version.
    DATABASE_ENDPOINT (string) : RDS or postGreSQL endpoint.
    DATABASE_NAME (string) : Database name.
    TABLE_NAME_AREA_30SPFAF06 (string) : Table name used for areas. Must exist
        on same database as used in rest of script.
    S3_INPUT_PATH_RIVERDISCHARGE (string) : AWS S3 input path for 
        riverdischarge.    
    S3_INPUT_PATH_DEMAND (string) : AWS S3 input path for 
        demand.     

"""

TESTING = 0
OVERWRITE_OUTPUT = 1
SCRIPT_NAME = 'Y2018M07D27_RH_Deltas_Apply_AridLowOnce_Mask_V01'
OUTPUT_VERSION = 3

DATABASE_ENDPOINT = "aqueduct30v05.cgpnumwmfcqc.eu-central-1.rds.amazonaws.com"
DATABASE_NAME = "database01"

INPUT_TABLE_NAME_RIGHT = "y2018m07d27_rh_deltas_arid_lowwateruse_full_ols_v01_v03"
INPUT_TABLE_NAME_LEFT = 'y2018m07d26_rh_deltas_ws_full_range_ols_v01_v03'

OUTPUT_TABLE_NAME = SCRIPT_NAME.lower() + "_v{:02.0f}".format(OUTPUT_VERSION)

print("Input Table Left: " , INPUT_TABLE_NAME_LEFT, 
      "Input Table Right: " , INPUT_TABLE_NAME_RIGHT, 
      "\nOutput Table: " , OUTPUT_TABLE_NAME)


# In[2]:

import time, datetime, sys
dateString = time.strftime("Y%YM%mD%d")
timeString = time.strftime("UTC %H:%M")
start = datetime.datetime.now()
print(dateString,timeString)
sys.version


# In[3]:

# imports
import re
import os
import numpy as np
import pandas as pd
import aqueduct3
from datetime import timedelta
from sqlalchemy import *
pd.set_option('display.max_columns', 500)


# In[4]:

F = open("/.password","r")
password = F.read().splitlines()[0]
F.close()

engine = create_engine("postgresql://rutgerhofste:{}@{}:5432/{}".format(password,DATABASE_ENDPOINT,DATABASE_NAME))
#connection = engine.connect()

if OVERWRITE_OUTPUT:
    sql = "DROP TABLE IF EXISTS {};".format(OUTPUT_TABLE_NAME)
    print(sql)
    result = engine.execute(sql)


# In[5]:

columns_to_keep = ["ols_ols10_arid_boolean_30spfaf06",
                   "ols_ols10_lowwateruse_boolean_30spfaf06",
                   "ols_ols10_aridandlowwateruse_boolean_30spfaf06"]


# In[6]:

sql = "CREATE TABLE {} AS".format(OUTPUT_TABLE_NAME)
sql += " SELECT l.*,"
for column_to_keep in columns_to_keep:
    sql += " r.{},".format(column_to_keep)
sql = sql[:-1]
sql += " FROM {} l".format(INPUT_TABLE_NAME_LEFT)
sql += " INNER JOIN {} r ON".format(INPUT_TABLE_NAME_RIGHT)
sql += " l.delta_id = r.delta_id"
sql += " WHERE r.year = 2014"


# In[7]:

print(sql)


# In[8]:

result = engine.execute(sql)


# In[9]:

sql_index = "CREATE INDEX {}delta_id ON {} ({})".format(OUTPUT_TABLE_NAME,OUTPUT_TABLE_NAME,"delta_id")


# In[10]:

sql_index


# In[11]:

result = engine.execute(sql_index)


# In[12]:

engine.dispose()


# In[13]:

end = datetime.datetime.now()
elapsed = end - start
print(elapsed)


# Previous runs:  
# 0:00:01.925743  
# 0:00:02.474701
# 
# 

# In[ ]:



