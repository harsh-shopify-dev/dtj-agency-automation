"""Pictures to a store through Shopify's staged upload (provision/staged_upload.py, 22 Oct 2026): the install service gives the
one-time addresses, the bytes go straight there, a dropped connection or a 5xx is tried again. Stand-ins play the install service and
Shopify's storage: nothing here reaches Shopify."""
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path

from provision import staged_upload as su


class StagedUpload(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.calls, self.posts = [], []

    def pic(self, name, data=b"\xff\xd8 picture"):
        p = self.dir / name
        p.write_bytes(data)
        return p

    def call(self, body):
        self.calls.append(body)
        return {"targets": [{"filename": f["filename"], "url": "https://shopify-staged-uploads.storage.googleapis.com/",
                             "resourceUrl": f"https://shopify-staged-uploads.storage.googleapis.com/tmp/1/{f['filename']}",
                             "parameters": [{"name": "key", "value": f"tmp/1/{f['filename']}"}, {"name": "policy", "value": "p"}]}
                            for f in body["files"]], "userErrors": ""}

    def post(self, statuses=None):
        statuses = list(statuses or [])

        def send(url, fields, filename, data, mime):
            self.posts.append((url, fields, filename, data, mime))
            nxt = statuses.pop(0) if statuses else 204
            if isinstance(nxt, Exception):
                raise nxt
            return nxt
        return send

    def test_every_picture_gets_its_resource_url(self):
        a, b = self.pic("1.jpg"), self.pic("banner.PNG", b"\x89PNG")
        urls = su.upload([a, b, a], call=self.call, shop="dtj-testing.myshopify.com", post=self.post(), sleep=lambda s: None)
        self.assertEqual(urls, {str(a): "https://shopify-staged-uploads.storage.googleapis.com/tmp/1/1.jpg",
                                str(b): "https://shopify-staged-uploads.storage.googleapis.com/tmp/1/banner.PNG"})
        self.assertEqual(self.calls, [{"op": "uploads", "shop": "dtj-testing.myshopify.com", "files": [
            {"filename": "1.jpg", "mimeType": "image/jpeg", "fileSize": 10}, {"filename": "banner.PNG", "mimeType": "image/png", "fileSize": 4}]}])
        self.assertEqual(len(self.posts), 2)  # the same picture twice is sent once
        url, fields, filename, data, mime = self.posts[0]
        self.assertEqual(fields, [("key", "tmp/1/1.jpg"), ("policy", "p")])
        self.assertEqual((filename, data, mime), ("1.jpg", b"\xff\xd8 picture", "image/jpeg"))

    def test_fifty_addresses_per_call(self):
        pics = [self.pic(f"{i}.webp") for i in range(51)]
        su.upload(pics, call=self.call, shop="s.myshopify.com", post=self.post(), sleep=lambda s: None)
        self.assertEqual([len(c["files"]) for c in self.calls], [50, 1])

    def test_only_pictures_of_a_sane_size(self):
        with self.assertRaisesRegex(ValueError, "only jpg, png, webp or gif"):
            su.upload([self.pic("clip.mp4")], call=self.call, shop="s.myshopify.com", post=self.post())
        with self.assertRaisesRegex(ValueError, "between 1 byte and 20 MB"):
            su.upload([self.pic("empty.jpg", b"")], call=self.call, shop="s.myshopify.com", post=self.post())
        self.assertEqual(self.calls, [])

    def test_a_dropped_connection_or_5xx_is_tried_again_then_stops(self):
        p = self.pic("1.jpg")
        waits = []
        su.upload([p], call=self.call, shop="s.myshopify.com", post=self.post([urllib.error.URLError("reset"), 503, 201]), sleep=waits.append)
        self.assertEqual((len(self.posts), waits), (3, [2, 4]))
        self.posts.clear()
        with self.assertRaisesRegex(su.UploadError, "refused it \\(HTTP 403\\)"):
            su.upload([p], call=self.call, shop="s.myshopify.com", post=self.post([403]), sleep=lambda s: None)
        self.assertEqual(len(self.posts), 1)  # a 4xx is final
        with self.assertRaisesRegex(su.UploadError, "did not answer"):
            su.upload([p], call=self.call, shop="s.myshopify.com", post=self.post([OSError("x")] * 3), sleep=lambda s: None)

    def test_a_missing_address_stops_with_shopifys_reason(self):
        p = self.pic("1.jpg")
        with self.assertRaisesRegex(su.UploadError, "gave no upload address \\(input.0: bad\\)"):
            su.upload([p], call=lambda b: {"targets": [{"filename": "1.jpg", "url": None}], "userErrors": "input.0: bad"},
                      shop="s.myshopify.com", post=self.post())
        with self.assertRaisesRegex(su.UploadError, "0 upload addresses for 1 pictures"):
            su.upload([p], call=lambda b: {"targets": []}, shop="s.myshopify.com", post=self.post())

    def test_the_multipart_body_puts_the_fields_first_and_the_file_last(self):
        body, ctype = su.multipart_body([("key", "tmp/1/a.jpg"), ("Content-Type", "image/jpeg")], "a.jpg", b"BYTES", "image/jpeg")
        boundary = ctype.split("boundary=")[1]
        self.assertTrue(ctype.startswith("multipart/form-data; boundary=dtj"))
        self.assertLess(body.index(b'name="key"'), body.index(b'name="file"; filename="a.jpg"'))
        self.assertIn(b"Content-Type: image/jpeg\r\n\r\nBYTES\r\n", body)
        self.assertTrue(body.endswith(f"--{boundary}--\r\n".encode()))


if __name__ == "__main__":
    unittest.main()
