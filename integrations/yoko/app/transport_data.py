"""Strict GTFS service-day and coordinate boundary conversions."""
import math
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from .core import fail

def gtfs_time_to_api(service_date,service_time,timezone="Asia/Tokyo"):
    if timezone!="Asia/Tokyo":
        fail("TIMEZONE_UNSUPPORTED","現在の国内プロファイルはAsia/Tokyoのみです")
    if not isinstance(service_date,str) or not re.fullmatch(r"\d{8}",service_date):
        fail("INVALID_SERVICE_DATE","営業日はYYYYMMDDで指定してください")
    if not isinstance(service_time,str) or not re.fullmatch(r"\d{2,3}:[0-5]\d:[0-5]\d",service_time):
        fail("INVALID_SERVICE_TIME","営業日の時刻はHH:MM:SSで指定してください（24時超対応）")
    try:
        day=date(int(service_date[:4]),int(service_date[4:6]),int(service_date[6:]))
    except ValueError:
        fail("INVALID_SERVICE_DATE","営業日が不正です")
    hour,minute,second=map(int,service_time.split(':'))
    return (datetime.combine(day,time(),ZoneInfo(timezone))+timedelta(hours=hour,minutes=minute,seconds=second)).isoformat()

def geojson_point_to_gtfs(point):
    if not isinstance(point,dict) or point.get('type')!='Point':
        fail("LOCATION_NOT_ACQUIRED","GeoJSON Pointの座標が必要です")
    coordinates=point.get('coordinates')
    if not isinstance(coordinates,list) or len(coordinates)!=2 or not all(type(x) in (int,float) and math.isfinite(x) for x in coordinates):
        fail("INVALID_COORDINATES","有限数の経度・緯度の順で指定してください")
    lon,lat=coordinates
    if not -180<=lon<=180 or not -90<=lat<=90:
        fail("INVALID_COORDINATES","座標の範囲が不正です")
    return {'stop_lat':lat,'stop_lon':lon}
