import requests
import cookielib
import fitbit
import MySQLdb
import datetime
from datetime import timedelta, date
import time

login_url = 'https://www.fitbit.com/login'

fitbit_username = 'FITBIT_USERNAME'
fitbit_password = 'FITBIT_PASSWORD'
consumer_ID = 'FITBIT_CONSUMER_ID'
consumer_secret = 'FITBIT_SECRET'

login_redir_value = '/oauth2/authorize?response_type=code&client_id=' + consumer_ID + '&scope=activity+nutrition+heartrate+location+nutrition+profile+settings+sleep+social+weight&state=6NwEPJlMJxczin6w0UenlBAYkNSnkv'

# DB Info

##CREATE TABLE IF NOT EXISTS `data` (
##  `id` int(11) NOT NULL AUTO_INCREMENT,
##  `type` varchar(80) NOT NULL,
##  `value` varchar(50) NOT NULL,
##  `time` datetime NOT NULL,
##  PRIMARY KEY (`id`)
##) ENGINE=MyISAM DEFAULT CHARSET=latin1 AUTO_INCREMENT=1 ;

conn = MySQLdb.connect (host = "DATABASE_SEVRVER",
                        user = "DATABASE_USERNAME",
                        passwd = "DATABASE_PASSWORD",
                        db = "DATABASE_DATABASE")
cursor = conn.cursor()

activities = [{'name': 'activities/steps', 'detail_level': '1min'}, {'name': 'activities/heart', 'detail_level': '1sec'}, {'name': 'activities/floors', 'detail_level': '1min'}, {'name': 'activities/elevation', 'detail_level': '1min'}, {'name': 'activities/distance', 'detail_level': '1min'}, {'name': 'activities/calories', 'detail_level': '1min'}]

#-----------------------------------------------------------------------------------------------------------------------

def db_insert(activity_name, date, time, value):
    dt = datetime.datetime.strptime(date + ' ' + time, "%Y-%m-%d %H:%M:%S")
    epoch = datetime.datetime.fromtimestamp(0)
    delta = dt - epoch
    unix_time = delta.total_seconds()
    sql_input = "INSERT INTO data (type, time, value) SELECT * FROM (SELECT '" + str(activity_name) + "', '" + str(unix_time) + "', '" + str(value) + "') AS tmp WHERE NOT EXISTS (SELECT id FROM data WHERE type = '" + str(activity_name) + "' and time = '" + str(unix_time) + "' and value = '" + str(value) + "') LIMIT 1"
    cursor.execute(sql_input)

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)

#-----------------------------------------------------------------------------------------------------------------------

import sys
while True:
    try: 
        # For 'intraday time series'
        ##start_date = date(2015, 9, 22)
        ##end_date = date(2015, 9, 28)

        sql_input = "select max(time) from data"
        cursor.execute(sql_input)
        last_value = cursor.fetchone()[0]

        #start_date = datetime.datetime.utcfromtimestamp(float(last_value)).date()
        start_date = (datetime.datetime.utcfromtimestamp(float(last_value))-datetime.timedelta(days=1)).date()
        end_date = date.today()

        print str(start_date) + " --> " + str(end_date)

        jar = cookielib.CookieJar()
        acc_pwd = {'login':'Log In','email':fitbit_username,'password':fitbit_password,'disableThirdPartyLogin':'false','redirect':login_redir_value,'includeWorkflow':'','switchToNonSecureOnRedirect':'','rememberMe':'false','_sourcePage':'iRBbbN8wUOHGrJMFkFsv6XbX0f6OV1Ndj1zeGcz7OKzA3gkNXMXGnj27D-H9WXS-','__fp':'3aGQGsug1l1ztQ7FkK21Ry2MI7JbqWTf', "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8 GTB7.1 (.NET CLR 3.5.30729)", "Referer": "http://example.com"}
        r = requests.get(login_url, cookies=jar)
        r = requests.post(login_url, cookies=jar, data=acc_pwd)
        return_uri = r.url
        return_split = return_uri.split('=')

        print return_split

        if 'code' in return_split[0]:
            return_code = return_split[1].split("&")[0]
            temp_client = fitbit.FitbitOauth2Client(consumer_ID, consumer_secret)
            token = temp_client.fetch_access_token(return_code, 'http://bensherwood.ca/fitbit_placeholder/')
        ##    access_token_value = token['access_token']
        ##    refresh_token_value = token['refresh_token']
        ##    expires_time = token['expires_at']

            for single_date in daterange(start_date, end_date):
                query_date = single_date.strftime("%Y-%m-%d")
                for activity_object in activities:
                    ####token = temp_client.refresh_token()
                    #token = temp_client.fetch_access_token(return_code, 'http://bensherwood.ca/fitbit_placeholder/')
                    access_token_value = token['access_token']
                    refresh_token_value = token['refresh_token']
                    expires_time = token['expires_at']
                    authd_client = fitbit.Fitbit(consumer_ID, consumer_secret, oauth2=True, access_token=access_token_value, refresh_token=refresh_token_value)
                    
                    activity_name = activity_object['name']
                    detail_level_value = activity_object['detail_level']
                    activity_time_series_data = authd_client.intraday_time_series(activity_name, base_date = query_date, detail_level = detail_level_value, start_time=None, end_time=None)

                    if activity_name == 'activities/steps':
                        print "Intraday - Steps - " + query_date
                        daily_steps = activity_time_series_data['activities-steps'][0]['value']
                        db_insert('activities-steps', query_date, '00:00:00', daily_steps)
                        steps_data = activity_time_series_data['activities-steps-intraday']['dataset']
                        for current_object in steps_data:
                            log_time = current_object['time']
                            steps_value = current_object['value']
                            db_insert('activities-steps-intraday', query_date, log_time, steps_value)

                    if activity_name == 'activities/heart':
                        print "Intraday - Heart - " + query_date
                        if 'restingHeartRate' in activity_time_series_data['activities-heart'][0]['value']:
                            daily_resting_heart_rate = activity_time_series_data['activities-heart'][0]['value']['restingHeartRate']
                            db_insert('activities-heart', query_date, '00:00:00', daily_resting_heart_rate)
                        heart_rate_data = activity_time_series_data['activities-heart-intraday']['dataset']
                        for current_object in heart_rate_data:
                            log_time = current_object['time']
                            heart_rate_value = current_object['value']
                            db_insert('activities-heart-intraday', query_date, log_time, heart_rate_value)

                    if activity_name == 'activities/floors':
                        print "Intraday - Floors - " + query_date
                        daily_floors = activity_time_series_data['activities-floors'][0]['value']
                        db_insert('activities-elevation', query_date, '00:00:00', daily_floors)
                        floors_data = activity_time_series_data['activities-floors-intraday']['dataset']
                        for current_object in floors_data:
                            log_time = current_object['time']
                            floors_value = current_object['value']
                            db_insert('activities-floors-intraday', query_date, log_time, floors_value)

                    if activity_name == 'activities/elevation':
                        print "Intraday - Elevation - " + query_date
                        daily_elevation = activity_time_series_data['activities-elevation'][0]['value']
                        db_insert('activities-floors', query_date, '00:00:00', daily_elevation)
                        elevation_data = activity_time_series_data['activities-elevation-intraday']['dataset']
                        for current_object in elevation_data:
                            log_time = current_object['time']
                            elevation_value = current_object['value']
                            db_insert('activities-elevation-intraday', query_date, log_time, elevation_value)

                    if activity_name == 'activities/distance':
                        print "Intraday - Distance - " + query_date
                        daily_distance = activity_time_series_data['activities-distance'][0]['value']
                        db_insert('activities-distance', query_date, '00:00:00', daily_distance)
                        distance_data = activity_time_series_data['activities-distance-intraday']['dataset']
                        for current_object in distance_data:
                            log_time = current_object['time']
                            distance_value = current_object['value']
                            db_insert('activities-distance-intraday', query_date, log_time, distance_value)

                    if activity_name == 'activities/calories':
                        print "Intraday - Calories - " + query_date
                        daily_calories = activity_time_series_data['activities-calories'][0]['value']
                        db_insert('activities-calories', query_date, '00:00:00', daily_calories)
                        calories_data = activity_time_series_data['activities-calories-intraday']['dataset']
                        for current_object in calories_data:
                            log_time = current_object['time']
                            calories_value = current_object['value']
                            db_insert('activities-calories-intraday', query_date, log_time, calories_value)

                    time.sleep(60)
    except:
        print "Error:", sys.exc_info()[0]
