
# coding: utf-8

# In[1]:

""" Copy data from S3 raw to S3 process.
-------------------------------------------------------------------------------
Copy files from S3 raw to S3 process data

Details:
    Author: Rutger Hofste
    Date: 20170731
    Kernel: python36
    Docker: rutgerhofste/gisdocker:ubuntu16.04

Args:

    SCRIPT_NAME (string) : Script name


Returns:


Result:  
    29 files will be copied to the output folder

Notes:
Copying all netCDF4 files from the raw data folder to process data folder. 
Before you run this script, please make sure the data is not already in the 
s3://wri-projects/Aqueduct30/processData/01PCRGlobWBV01 folder

"""

# Input Parameters

SCRIPT_NAME = "Y2017M07D31_RH_copy_S3raw_s3process_V02"

S3_INPUT_PATHS = ["s3://wri-projects/Aqueduct30/rawData/Utrecht/yoshi20161219/waterdemand",
               "s3://wri-projects/Aqueduct30/rawData/Utrecht/additionalFiles/wateravailability",
               "s3://wri-projects/Aqueduct30/rawData/Utrecht/yoshi20161219/wateravailability",
               "s3://wri-projects/Aqueduct30/rawData/Utrecht/yoshi20161219/waterstress",
               "s3://wri-projects/Aqueduct30/rawData/Utrecht/additionalFiles/soilmoisture",
               "s3://wri-projects/Aqueduct30/rawData/Utrecht/yoshi20161219/indicators"]


# Output Parameters

S3_OUTPUT_PATH = "s3://wri-projects/Aqueduct30/processData/{}/output".format(SCRIPT_NAME)


# In[2]:

import time, datetime, sys
dateString = time.strftime("Y%YM%mD%d")
timeString = time.strftime("UTC %H:%M")
start = datetime.datetime.now()
print(dateString,timeString)
sys.version


# In[3]:

# Imports
import subprocess


# In[4]:

# ETL
result_list = []
for S3_input_path in S3_INPUT_PATHS:
    command = "aws s3 cp {} {} --recursive".format(S3_input_path,S3_OUTPUT_PATH) 
    result = subprocess.check_output(command,shell=True)
    result_list = result_list + [result]
    print(command)



# In[5]:

end = datetime.datetime.now()
elapsed = end - start
print(elapsed)
