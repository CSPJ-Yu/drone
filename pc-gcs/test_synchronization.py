import unittest
from drone_gcs.synchronization import TelemetryHistory, describe
from drone_gcs.telemetry import TelemetryState


class SynchronizationTests(unittest.TestCase):
    def test_matches_only_past_and_copies_state(self):
        history = TelemetryHistory()
        state = TelemetryState(received_at=10, roll=2, attitude_at=10)
        history.add(state)
        state.roll = 999
        history.add(TelemetryState(received_at=12, roll=5, attitude_at=12))
        frame = history.frame(None, 7, 11)
        self.assertEqual(frame.context.telemetry.roll, 2)
        self.assertEqual(frame.context.available_at, 11)
        self.assertIsNone(history.match(9))
        history.add(TelemetryState(received_at=13, roll=8))
        self.assertEqual(frame.context.telemetry.roll, 2)

    def test_per_field_staleness_and_no_fix(self):
        history = TelemetryHistory()
        history.add(TelemetryState(received_at=20, heartbeat_at=20,
            attitude_at=10, position_at=20, gps_at=20, gps_fix=1,
            latitude=35, longitude=139, altitude=50))
        description = describe(history.frame(None, 1, 20.1).context)
        self.assertIn('Attitude: STALE', description)
        self.assertIn('GPS: NO FIX', description)
        self.assertNotIn('35.0000000', description)

    def test_valid_position_and_retention(self):
        history = TelemetryHistory()
        history.add(TelemetryState(received_at=1))
        history.add(TelemetryState(received_at=30, position_at=30, gps_at=30,
            gps_fix=3, latitude=0, longitude=0, altitude=50))
        self.assertEqual(len(history.states), 1)
        self.assertIn('0.0000000, 0.0000000', describe(history.frame(None, 2, 30.1).context))


if __name__ == '__main__':
    unittest.main()
