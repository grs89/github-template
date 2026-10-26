import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import upload_defectdojo

class TestUploadDefectDojo(unittest.TestCase):

    @patch("requests.post")
    def test_upload_scan_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        # Create dummy temp file
        test_file = "/tmp/test_report.json"
        with open(test_file, "w") as f:
            f.write("{}")

        try:
            result = upload_defectdojo.upload_scan(
                url="http://192.168.10.159:8089",
                token="test-token",
                product="TestProduct",
                engagement="TestEngagement",
                scan_type="Trivy Scan",
                file_path=test_file
            )
            self.assertTrue(result)
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertIn("Authorization", kwargs["headers"])
            self.assertEqual(kwargs["headers"]["Accept"], "application/json")
            self.assertEqual(kwargs["data"]["product_name"], "TestProduct")
            self.assertEqual(kwargs["data"]["product_type_name"], "Research and Development")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch("requests.post")
    def test_upload_scan_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid file"}
        mock_post.return_value = mock_response

        test_file = "/tmp/test_fail.json"
        with open(test_file, "w") as f:
            f.write("{}")

        try:
            result = upload_defectdojo.upload_scan(
                url="http://192.168.10.159:8089",
                token="test-token",
                product="TestProduct",
                engagement="TestEngagement",
                scan_type="Trivy Scan",
                file_path=test_file
            )
            self.assertFalse(result)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    @patch.dict(os.environ, {
        "DEFECTDOJO_URL": "http://defectdojo_nginx:8080",
        "DEFECTDOJO_TOKEN": "valid-token"
    })
    @patch("upload_defectdojo.upload_scan")
    @patch("glob.glob")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=100)
    def test_main_exits_with_error_on_failed_upload(self, mock_size, mock_exists, mock_glob, mock_upload):
        mock_glob.side_effect = lambda pat: ["gl-sast-report.json"] if "gl-sast-report.json" in pat else []
        mock_upload.return_value = False  # Simula fallo en la carga

        with self.assertRaises(SystemExit) as cm:
            upload_defectdojo.main()
        self.assertEqual(cm.exception.code, 1)

    @patch.dict(os.environ, {
        "DEFECTDOJO_URL": "http://192.168.10.159:8089",
        "DEFECTDOJO_TOKEN": "valid-token"
    })
    @patch("upload_defectdojo.upload_scan")
    @patch("glob.glob")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=100)
    def test_main_succeeds_when_all_uploads_pass(self, mock_size, mock_exists, mock_glob, mock_upload):
        mock_glob.side_effect = lambda pat: ["gl-sast-report.json"] if "gl-sast-report.json" in pat else []
        mock_upload.return_value = True  # Simula éxito

        try:
            upload_defectdojo.main()
        except SystemExit:
            self.fail("main() raised SystemExit unexpectedly on success!")

    def test_sanitize_report_timestamps(self):
        test_file = "/tmp/test_sanitize_timestamps.json"
        sample_data = {
            "version": "15.0.0",
            "scan": {
                "start_time": "2026-09-10T16:45:12.287941+00:00",
                "end_time": "2026-09-10T16:45:13.999999+00:00"
            }
        }
        with open(test_file, "w") as f:
            import json
            json.dump(sample_data, f)

        try:
            upload_defectdojo.sanitize_report_timestamps(test_file)
            with open(test_file, "r") as f:
                import json
                cleaned = json.load(f)
            self.assertEqual(cleaned["scan"]["start_time"], "2026-09-10T16:45:12")
            self.assertEqual(cleaned["scan"]["end_time"], "2026-09-10T16:45:13")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == "__main__":
    unittest.main()
