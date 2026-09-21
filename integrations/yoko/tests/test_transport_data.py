import unittest
from app.core import DomainError
from app.transport_data import geojson_point_to_gtfs,gtfs_time_to_api

class TransportBoundaryTests(unittest.TestCase):
    def test_gtfs_after_midnight_preserves_service_day_and_timezone(self):
        self.assertEqual(gtfs_time_to_api('20261231','26:05:01'),'2027-01-01T02:05:01+09:00')
        self.assertEqual(gtfs_time_to_api('20260919','00:00:00'),'2026-09-19T00:00:00+09:00')
    def test_invalid_service_dates_times_and_unsupported_timezone(self):
        for day,clock,tz in [('20260230','10:00:00','Asia/Tokyo'),('20260919','24:60:00','Asia/Tokyo'),('2026-09-19','12:00:00','Asia/Tokyo'),('20260919','12:00:00','UTC')]:
            with self.assertRaises(DomainError):gtfs_time_to_api(day,clock,tz)
    def test_geojson_longitude_latitude_maps_to_named_gtfs_fields(self):
        self.assertEqual(geojson_point_to_gtfs({'type':'Point','coordinates':[139.5,35.5]}),{'stop_lat':35.5,'stop_lon':139.5})
        self.assertEqual(geojson_point_to_gtfs({'type':'Point','coordinates':[0,0]}),{'stop_lat':0,'stop_lon':0})
    def test_unknown_or_invalid_location_is_never_zero_filled(self):
        for point in [None,{}, {'type':'Point','coordinates':[]},{'type':'Point','coordinates':[35.5,139.5]},{'type':'Point','coordinates':[True,35]},{'type':'Point','coordinates':[float('nan'),35]}]:
            with self.assertRaises(DomainError):geojson_point_to_gtfs(point)
