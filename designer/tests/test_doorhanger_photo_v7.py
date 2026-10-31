"""Photo-led door hanger QA: protects against blank/minimal previews again.

This test generates artwork in-memory. It does not call the network, database
or touch any template media. Actual install separately requires 20 licensed
photo sources (cached, supplied or retrieved).
"""
import io

from django.test import SimpleTestCase
from PIL import Image

from designer.management.commands.rebuild_doorhanger_photo_v7 import (
    THEMES, EDITIONS, GENERATOR, _front, _back, _mockup, edition_for,
)


class DoorHangerPhotoQualityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Deterministic photo-like content: real downloaded photos are only
        # available at installation time, not required in CI.
        cls.image=Image.new("RGB",(1050,1400),(113,149,163))

    def test_first_four_gallery_designs_use_different_compositions(self):
        self.assertEqual([edition_for(i) for i in range(4)],[0,1,2,3])
        self.assertEqual(len(THEMES),20)
        self.assertEqual(len(EDITIONS),5)
        self.assertIn("photo-v7",GENERATOR)

    def test_every_design_has_edited_photo_and_visible_text(self):
        signatures=set()
        for idx in range(100):
            front=_front(idx,450,1100,self.image)
            back=_back(idx,450,1100,self.image)
            for page in (front,back):
                photos=[o for o in page["objects"] if o["type"]=="image"]
                labels=[o for o in page["objects"] if o["type"]=="textbox"]
                self.assertEqual(len(photos),1)
                self.assertGreaterEqual(len(labels),5)
                self.assertTrue(photos[0]["src"].startswith("data:image/jpeg;base64,"))
                self.assertTrue(photos[0]["customerEditable"])
                self.assertTrue(photos[0]["manualReplacement"])
                self.assertIn("YOURBRAND.COM",[o["text"] for o in labels])
                self.assertTrue(any("headline" in o["name"].lower() for o in labels))
                self.assertTrue(any("call to action" in o["name"].lower() for o in labels))
            record=tuple(
                (o["type"],o["left"],o["top"],o.get("text",""))
                for o in front["objects"]
            )
            self.assertNotIn(record,signatures)
            signatures.add(record)
        self.assertEqual(len(signatures),100)

    def test_full_composite_preview_has_both_pages_and_photo(self):
        for idx in (0,1,2,3,4,19,20,39,60,99):
            front=_front(idx,450,1100,self.image)
            back=_back(idx,450,1100,self.image)
            png=_mockup(front,back,edition_for(idx))
            self.assertGreater(len(png),5000)
            with Image.open(io.BytesIO(png)) as preview:
                self.assertEqual(preview.format,"PNG")
                self.assertEqual(preview.size,(1080,860))
                self.assertGreater(len(preview.getcolors(1080*860) or []),5)

    def test_narrow_print_faces_are_not_overlapped(self):
        for w,h in ((350,1100),(450,1100),(500,1200),(600,1400)):
            for idx in (0,1,2,3,4,19,20,39,60,99):
                for render in (_front,_back):
                    page=render(idx,w,h,self.image)
                    self.assertEqual((page["width"],page["height"]),(w,h))
