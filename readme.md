# Sharkalytics
This is the source code for Sharkalytics, a site that collects and crunches the numbers behind ABC's _Shark Tank_. The application is currently live at [www.sharkalytics.com](http://www.sharkalytics.com).

Sharkalytics is hosted on Google App Engine, with data stored in [Google Cloud SQL](https://cloud.google.com/appengine/docs/python/cloud-sql/). 

# Setup
To get your version running, you'll need to create a file in your root directory called *privatevariables.py*. The file should include a list as shown below. All are required.

    INSTANCE_NAME = 'your-project-id:your-instance-name' # for Google Cloud SQL
    database_name='YOUR_DATABASE'
    user='NAME_OF_YOUR_APP'
    passwd='YOUR_PASSWD'
    flagged_terms = ['Java'] # list of unwelcome UA strings
    flagged_IPs = ['127.0.0.1'] # list of unwelcome IP addresses... not your own, probably!
    Google_Analytics_ID = 'UA-XXXXXXXX-X'

You'll also need to change the application name in *app.yaml* to something that hasn't been used already.

# The data
The Sharkalytics database is hosted in Google Cloud SQL. This repository includes a schema that you can use to start your own. See *sharkbase.sql*.