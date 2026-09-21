"""Regression checks from the 2026-09-21 official-source code audit.

Real loopback HTTP + the unchanged official OpenAPI. No outside counterpart.
"""
from datetime import datetime
import http.client
import json
import socket
import threading
from unittest.mock import patch
from tests import test_booking as booking
from tests import test_catalog as catalog
from tests.test_core import REQUEST
from app.mlit import reservation, reservation_request
from app.server import Handler


class AuditHTTPTests(booking.BookingFixture):
    start = catalog.CatalogHTTPTests.start
    stop = catalog.CatalogHTTPTests.stop
    request = catalog.CatalogHTTPTests.request
    login = catalog.CatalogHTTPTests.login
    client_write = catalog.CatalogHTTPTests.client_write
    update_headers = catalog.CatalogHTTPTests.update_headers

    def setUp(self):
        super().setUp()
        # A UTC date differs from the local planned pickup date at this boundary.
        self.now = datetime.fromisoformat('2026-09-20T23:55:00+09:00').timestamp()
        self.ready()
        self.start()
        self.server.core.clock = self.core.clock
        self.addCleanup(self.stop)

    def standard_body(self, ride, status=None):
        value = reservation(ride)
        fields = ('passenger_id', 'service_id', 'pickup', 'dropoff',
                  'passenger_count', 'accessibility_feature_count', 'status')
        result = {key: value[key] for key in fields}
        if status is not None:
            result['status'] = status
        return result

    def test_standard_cannot_change_stops_even_if_core_owner_approved_it(self):
        ride = self.create()
        op = self.prepare('change', {'ride_id': ride['id'], **REQUEST, 'destination_stop_id': 'stop-c'})
        body = self.standard_body({**ride, **op['payload']['details']})
        grant = self.grant(op)
        code, problem = self.request('/reservations/' + ride['id'], 'PUT', body, grant,
                                     headers=self.update_headers(op))
        self.assertEqual((code, problem['title']), (400, 'STANDARD_ROUTE_CHANGE_UNSUPPORTED'))
        self.assertEqual(self.core.get_ride('rider-a1', ride['id'])['destination_stop_id'], 'stop-b')
        # The independent Web/direct API contract still allows this operation.
        code, value = self.client_write(op, grant)
        self.assertEqual((code, value['current']['destination_stop_id']), (200, 'stop-c'))

    def test_standard_update_accepts_unchanged_optional_vehicle(self):
        ride = self.execute(self.booking())
        op = self.prepare('change', {'ride_id': ride['id'], **REQUEST, 'passengers': 2})
        body = self.standard_body({**ride, **op['payload']['details']})
        body['vehicle'] = reservation(ride)['vehicle']
        code, value = self.request('/reservations/' + ride['id'], 'PUT', body, self.grant(op),
                                   headers=self.update_headers(op))
        self.assertEqual(code, 200, value)
        self.assertEqual(value['vehicle'], body['vehicle'])
        self.assertEqual(value['passenger_count'][0]['count'], 2)

    def test_standard_update_rejects_vehicle_change_without_consuming_approval(self):
        ride = self.execute(self.booking())
        op = self.prepare('cancel', {'ride_id': ride['id']})
        body = self.standard_body(ride, 'cancelled')
        body['vehicle'] = reservation(ride)['vehicle'] | {'id': 'different-vehicle'}
        grant = self.grant(op)
        code, problem = self.request('/reservations/' + ride['id'], 'PUT', body, grant,
                                     headers=self.update_headers(op))
        self.assertEqual((code, problem['title']), (403, 'APPROVAL_MISMATCH'))
        self.assertEqual(self.core.get_ride('rider-a1', ride['id'])['status'], 'assigned')
        body['vehicle'] = reservation(ride)['vehicle']
        self.assertEqual(self.request('/reservations/' + ride['id'], 'PUT', body, grant,
                                      headers=self.update_headers(op))[0], 200)

    def test_standard_vehicle_allows_omitted_capacity_but_requires_id_and_name(self):
        ride = self.execute(self.booking())
        op = self.prepare('cancel', {'ride_id': ride['id']})
        body = self.standard_body(ride, 'cancelled')
        value = reservation(ride)['vehicle']
        grant = self.grant(op)
        for vehicle in [{'id': value['id']}, {'name': value['name']},
                        {'id': value['id'], 'name': value['name'], 'unexpected': True}]:
            body['vehicle'] = vehicle
            code, problem = self.request('/reservations/' + ride['id'], 'PUT', body, grant,
                                         headers=self.update_headers(op))
            self.assertEqual((code, problem['title']), (403, 'APPROVAL_MISMATCH'))
            self.assertEqual(self.core.get_ride('rider-a1', ride['id'])['status'], 'assigned')
        body['vehicle'] = {key: value[key] for key in ('id', 'name')}
        code, result = self.request('/reservations/' + ride['id'], 'PUT', body, grant,
                                    headers=self.update_headers(op))
        self.assertEqual((code, result['status']), (200, 'cancelled'))

    def test_explicit_radius_requires_location_even_at_default_value_or_with_id(self):
        grant = self.grant()
        for query in ['radius=500', 'radius=100', 'stop_ids=stop-a&radius=500']:
            code, problem = self.request('/stops?' + query, grant=grant)
            self.assertEqual((code, problem['title']), (400, 'INVALID_QUERY'))
        # Omitting radius is valid; the default only applies to location search.
        for query in ['', '?stop_ids=stop-a']:
            code, value = self.request('/stops' + query, grant=grant)
            self.assertEqual(code, 200, value)

    def test_unknown_vehicle_name_is_omitted_and_not_invented(self):
        ride = self.driver('accept', self.create(), 'driver-a2')
        code, value = self.request('/passengers/rider-a1/reservations', grant=self.grant())
        self.assertEqual(code, 200, value)
        self.assertNotIn('vehicle', value['reservations'][0])
        self.assertIsNotNone(self.core.get_ride('rider-a1', ride['id'])['vehicle_id'])

    def test_date_filters_use_jst_include_endpoints_and_allow_either_bound(self):
        self.execute(self.booking())
        endpoint = '/passengers/rider-a1/reservations'
        grant = self.grant()
        for query, count in [('pickup_date_from=2026-09-21', 1),
                             ('pickup_date_to=2026-09-20', 0),
                             ('pickup_date_to=2026-09-21', 1),
                             ('pickup_date_from=2026-09-21&pickup_date_to=2026-09-21', 1),
                             ('pickup_date_from=2026-09-22', 0)]:
            with self.subTest(query=query):
                code, value = self.request(endpoint + '?' + query, grant=grant)
                self.assertEqual((code, value['total']), (200, count), value)

    def test_date_filters_precede_pagination_and_owner_boundary(self):
        rides = [self.execute(self.booking()) for _ in range(2)]
        self.execute(self.booking(self.candidate('rider-a2'), 'rider-a2'), 'rider-a2')
        code, value = self.request('/passengers/rider-a1/reservations?pickup_date_from=2026-09-21&offset=1&limit=1', grant=self.grant())
        self.assertEqual((code, value['total'], len(value['reservations'])), (200, 2, 1))
        self.assertIn(value['reservations'][0]['id'], [r['id'] for r in rides])
        self.assertEqual(self.request('/passengers/rider-a1/reservations?pickup_date_from=2026-09-21', grant=self.grant(actor='rider-a2'))[0], 403)

    def test_unknown_planned_date_is_explicit_not_silently_dropped(self):
        booked = self.execute(self.booking())
        self.create()
        endpoint = '/passengers/rider-a1/reservations?pickup_date_from=2026-09-21'
        code, problem = self.request(endpoint, grant=self.grant())
        self.assertEqual((code, problem['title']), (500, 'PICKUP_TIME_NOT_ACQUIRED'))
        code, value = self.request(endpoint + '&reservation_ids=' + booked['id'], grant=self.grant())
        self.assertEqual((code, value['total']), (200, 1))
        code, value = self.request(endpoint + '&status=confirmed', grant=self.grant())
        self.assertEqual((code, value['total']), (200, 1))

    def test_date_filter_invalid_range_and_empty_result_do_not_create_rides(self):
        endpoint = '/passengers/rider-a1/reservations'
        code, problem = self.request(endpoint + '?pickup_date_from=2026-09-22&pickup_date_to=2026-09-21', grant=self.grant())
        self.assertEqual((code, problem['title']), (400, 'INVALID_QUERY'))
        code, value = self.request(endpoint + '?pickup_date_to=2026-09-21', grant=self.grant())
        self.assertEqual((code, value['total']), (200, 0))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])

    def test_candidate_each_required_field_is_required_even_empty_accessibility(self):
        body = booking.BookingHTTPTests.query(self)
        grant = self.grant()
        for field in body:
            with self.subTest(missing=field):
                incomplete = {key: value for key, value in body.items() if key != field}
                code, problem = self.request('/reservations/candidates', 'POST', incomplete, grant)
                self.assertEqual((code, problem['title']), (400, 'SCHEMA_INVALID'))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])
        self.assertEqual(self.request('/reservations/candidates', 'POST', body, grant)[0], 200)

    def test_standard_timeout_after_commit_reconciles_and_retries_without_second_seat(self):
        op = self.booking()
        grant = self.grant(op)
        body = reservation_request(op['payload']['details'], 'rider-a1')
        committed, release, done = threading.Event(), threading.Event(), threading.Event()
        original = Handler.reply

        def delayed_reply(handler, status, data, *args, **kwargs):
            if handler.path == '/reservations' and status == 201 and not committed.is_set():
                committed.set()  # Core has already committed before the reply.
                try:
                    release.wait(2)
                    return original(handler, status, data, *args, **kwargs)
                finally:
                    done.set()
            return original(handler, status, data, *args, **kwargs)

        headers = {'Authorization': 'Bearer ' + grant['access_token'],
                   'X-Client-ID': grant['client_id'], 'Content-Type': 'application/json',
                   **self.update_headers(op)}
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=0.05)
        with patch.object(Handler, 'reply', delayed_reply):
            try:
                conn.request('POST', '/reservations', json.dumps(body), headers)
                self.assertTrue(committed.wait(1), 'The timeout must occur after a real commit')
                with self.assertRaises(socket.timeout):
                    conn.getresponse()
            finally:
                conn.close()
                release.set()
                done.wait(2)
        code, receipt = self.request('/direct/v1/operations/' + op['operation_id'], grant=grant)
        self.assertEqual(code, 200, receipt)
        code, replay = self.request('/reservations', 'POST', body, grant,
                                    headers=self.update_headers(op))
        self.assertEqual((code, replay['id']), (201, receipt['current']['id']))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(1,)])
        self.assertEqual(self.sql('SELECT reserved FROM runs'), [(1,)])
