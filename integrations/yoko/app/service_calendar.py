"""Operating calendar shared by admission, planned rides and GTFS export.

Intervals are UTC epoch seconds with an inclusive start and exclusive end.
Special dates override holidays, which override the weekly calendar. A closed
date does not cancel a preceding service day's explicitly configured 24h+ tail.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DAYS=('monday','tuesday','wednesday','thursday','friday','saturday','sunday','holidays')

def daily_slots(profile, day):
    key=day.isoformat()
    for special in profile['special_operating_hours']:
        if special['date']==key:return special['time_slots']
    return profile['operating_hours']['holidays' if key in profile['holiday_dates'] else DAYS[day.weekday()]]

def merge_windows(windows):
    merged=[]
    for start,end in sorted(windows):
        if merged and start<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
        else:merged.append([start,end])
    return merged

def operating_windows(profile, first, last, timezone):
    zone=ZoneInfo(timezone);windows=[];day=first
    while day<=last:
        midnight=datetime.combine(day,datetime.min.time(),zone).timestamp()
        windows.extend((midnight+s['start_time_offset_sec'],midnight+s['end_time_offset_sec']) for s in daily_slots(profile,day))
        day+=timedelta(days=1)
    return merge_windows(windows)
