"""Regression tests: door-hanger previews must never be blank colour fields.

Run with Django's existing test runner. No DB, network or media writes.
"""
import hashlib
import json
import unittest

from django.test import SimpleTestCase
from designer.management.commands.rebuild_doorhanger_luxury_100 import (
    GENERATOR, THEMES, EDITIONS, page_for, svg_preview,
)


class DoorHangerLuxuryTests(SimpleTestCase):
    def test_exactly_100_unique_layouts_with_front_and_back(self):
        self.assertEqual(len(THEMES), 20)
        self.assertEqual(len(EDITIONS), 5)
        signatures=set()
        for idx in range(100):
            pages=[page_for(idx,side,450,1100) for side in (0,1)]
            self.assertEqual([p["name"] for p in pages], ["Front","Back"])
            for page in pages:
                elements=page["objects"]
                self.assertGreaterEqual(len(elements),12)
                texts=[o for o in elements if o["type"]=="textbox"]
                self.assertGreaterEqual(len(texts),5)
                self.assertTrue(all(o["customerEditable"] for o in texts))
                self.assertFalse(any(o.get("backgroundAsset") for o in texts))
                self.assertTrue(any(o["type"] in ("circle","ellipse") for o in elements))
                for obj in elements:
                    self.assertGreaterEqual(obj["left"],0)
                    self.assertGreaterEqual(obj["top"],0)
                    self.assertLessEqual(obj["left"]+obj["width"],450.2)
                    self.assertLessEqual(obj["top"]+obj["height"],1100.2)
            front=pages[0]
            rendered=svg_preview(front)
            self.assertIn("<svg",rendered)
            self.assertIn("<text ",rendered)
            self.assertIn("<circle",rendered)
            self.assertIn("mask=",rendered)
            self.assertIn("YOURBRAND.COM",rendered)
            brand=THEMES[idx%20][0]
            self.assertIn(brand.replace("&","&amp;"),rendered)
            key=hashlib.sha256(json.dumps([
                [(o["type"],o["left"],o["top"],o.get("text")) for o in p["objects"]]
                for p in pages
            ]).encode()).hexdigest()
            self.assertNotIn(key,signatures)
            signatures.add(key)
        self.assertEqual(len(signatures),100)

    def test_narrow_door_hanger_has_no_collisions(self):
        # Wider/narrower Admin canvases still must retain bounds.
        for dimensions in ((350,1100),(450,1100),(500,1200),(600,1400)):
            width,height=dimensions
            for idx in range(100):
                for side in (0,1):
                    page=page_for(idx,side,width,height)
                    self.assertEqual((page["width"],page["height"]),dimensions)
                    self.assertGreaterEqual(len(page["objects"]),12)

    def test_preview_comes_from_editable_fields(self):
        page=page_for(0,0,450,1100)
        page["objects"][-1]["text"]="CUSTOM MESSAGE"
        svg=svg_preview(page)
        self.assertIn("CUSTOM MESSAGE",svg)
        self.assertNotIn("Replace photo",svg)
        self.assertNotIn("Zenvibe",svg)

    def test_generator_is_not_legacy_background_only(self):
        self.assertIn("luxury-v6",GENERATOR)
        for idx in range(100):
            page=page_for(idx,0,450,1100)
            texts=[o for o in page["objects"] if o["type"]=="textbox"]
            self.assertGreaterEqual(len(texts),5)
            self.assertTrue(any("headline" in o["name"].lower() for o in texts))
            self.assertTrue(any("call to action" in o["name"].lower() for o in texts))
