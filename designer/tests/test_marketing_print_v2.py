"""Quality gates for all 100 Flyers, 100 bi-fold and 100 tri-fold masters.

No network or Django DB writes. Tests the actual printing panel boundaries,
per-object editability, photo placement, preview fidelity and saved-page count.
"""
from __future__ import annotations

import io

from django.test import SimpleTestCase
from PIL import Image

from designer.management.commands.rebuild_remaining_premium_100 import (
    PrintPage, canvas_size, physical_region,
)
from designer.management.commands.rebuild_premium_marketing_print_v2 import (
    GENERATOR, TARGET, _panel_role, _safe_panel, make_marketing_page,
    _preview, product_kind,
)
from designer.tests.test_remaining_premium_100 import FakeProduct, FakePhotos


class MarketingKindTests(SimpleTestCase):
    def test_only_three_marketing_families_are_eligible(self):
        for name, expected in (
            ("Custom Flyers","flyer"),
            ("Premium Bi-Fold Brochures Printing","bifold"),
            ("Custom tri-fold brochures","trifold"),
            ("Standard Business Cards",""),
            ("Custom Wall Calendars",""),
            ("10x10 FT Custom Canopy Tent",""),
            ("Custom Invitation Cards",""),
            ("Premium Custom Tickets",""),
        ):
            with self.subTest(name=name):
                self.assertEqual(
                    product_kind(FakeProduct(name,"marketing-materials")),expected
                )
        self.assertEqual(
            product_kind(FakeProduct("Custom Flyers","promotional-products")),""
        )
        self.assertEqual(TARGET,100)
        self.assertIn("premium",GENERATOR)

    def test_true_outside_and_inside_print_order(self):
        self.assertEqual(
            [_panel_role("bifold",0,i) for i in range(2)],
            ["back","cover"]
        )
        self.assertEqual(
            [_panel_role("bifold",1,i) for i in range(2)],
            ["story","services"]
        )
        self.assertEqual(
            [_panel_role("trifold",0,i) for i in range(3)],
            ["flap","back","cover"]
        )
        self.assertEqual(
            [_panel_role("trifold",1,i) for i in range(3)],
            ["story","services","contact"]
        )


class PremiumPanelLayoutTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank=FakePhotos()

    def test_panel_artwork_never_crosses_fold_positions(self):
        product=FakeProduct("Custom tri-fold brochures","marketing-materials")
        surface=PrintPage("Outside",11,8.5,11,8.5,(0,0,1,1))
        W,H=canvas_size(surface)
        region=physical_region(product,surface,W,H)
        for count in (2,3):
            for j in range(count):
                x,y,w,h=_safe_panel(surface,region,j,count)
                self.assertGreaterEqual(x,W*j/count+1)
                self.assertLessEqual(x+w,W*(j+1)/count-1)
                self.assertGreater(w,90)

    def test_100_flyer_bifold_trifold_designs_are_distinct_and_editable(self):
        cases=(
            ("Custom Flyers","flyer",PrintPage("Front",8.5,11,8.5,11,(0,0,1,1)),1),
            ("Premium Bi-Fold Brochures","bifold",
             PrintPage("Outside",11,8.5,11,8.5,(0,0,1,1)),2),
            ("Custom Tri-Fold Brochures","trifold",
             PrintPage("Outside",11,8.5,11,8.5,(0,0,1,1)),3),
        )
        for name,kind,surface,count in cases:
            product=FakeProduct(name,"marketing-materials")
            signatures=set()
            for idx in range(100):
                pages=[make_marketing_page(product,kind,idx,side,surface,self.bank)
                       for side in range(1 if kind=="flyer" else 2)]
                for page in pages:
                    self.assertEqual(
                        page["foldPanelCount"],count
                    )
                    self.assertEqual(
                        len(page["foldGuides"]),count-1
                    )
                    self.assertEqual(page["physical"]["unit"],"in")
                    objects=page["objects"]
                    texts=[o for o in objects if o["type"]=="textbox"]
                    photos=[o for o in objects if o["type"]=="image"]
                    self.assertGreaterEqual(len(texts),count*4)
                    self.assertGreaterEqual(len(photos),count)
                    self.assertTrue(all(o["customerEditable"] for o in texts+photos))
                    self.assertTrue(all(
                        str(o.get("src","")).startswith("data:image/jpeg;base64,")
                        for o in photos
                    ))
                    self.assertTrue(all("Fold" not in o["name"] for o in objects))
                    for o in objects:
                        self.assertGreaterEqual(o["left"],0)
                        self.assertGreaterEqual(o["top"],0)
                        self.assertLessEqual(o["left"]+o["width"],page["width"]+.2)
                        self.assertLessEqual(o["top"]+o["height"],page["height"]+.2)
                signature=tuple(
                    (o["type"],o["left"],o["top"],o.get("text"))
                    for page in pages for o in page["objects"]
                )
                self.assertNotIn(signature,signatures)
                signatures.add(signature)
            self.assertEqual(len(signatures),100)

    def test_gallery_preview_renders_real_photo_and_two_pages(self):
        surface=PrintPage("Outside",11,8.5,11,8.5,(0,0,1,1))
        for kind in ("flyer","bifold","trifold"):
            product=FakeProduct(
                {"flyer":"Custom Flyers","bifold":"Premium Bi-Fold Brochures",
                 "trifold":"Custom Tri-Fold Brochures"}[kind],
                "marketing-materials")
            for idx in (0,1,2,3,4,19,20):
                pages=[make_marketing_page(product,kind,idx,side,surface,self.bank)
                       for side in range(1 if kind=="flyer" else 2)]
                data=_preview(pages,kind)
                self.assertGreater(len(data),8000)
                with Image.open(io.BytesIO(data)) as img:
                    self.assertEqual(img.size,(900,1160))
                    self.assertEqual(img.format,"PNG")
                    self.assertGreater(len(img.getcolors(900*1160) or []),25)
