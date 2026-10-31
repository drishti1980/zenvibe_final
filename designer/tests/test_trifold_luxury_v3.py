"""Tri-fold luxury V3 offline regression checks.

These tests use generated local photo-like pixels only for geometry testing.
The real installer uses curated licensed photo assets and fails safely if its
photography is unavailable. Tests never access Zenvibe.ca or modify the DB.
"""
import io
import re

from django.test import SimpleTestCase
from PIL import Image, ImageDraw

from designer.management.commands.rebuild_remaining_premium_100 import (
    PrintPage, _jpeg, canvas_size, physical_region,
)
from designer.management.commands.rebuild_trifold_luxury_v3 import (
    GENERATOR, COUNT, DIRECTIONS, FEATURES, _page_panel, _panel_role,
    _existing, _preview, build_page, is_trifold, art_direction,
)
from designer.tests.test_remaining_premium_100 import FakeProduct


class PhotoFixture:
    def __init__(self):
        self.images={}
    def crop(self,theme,aspect,edition):
        key=(theme,round(aspect,2),edition)
        if key not in self.images:
            picture=Image.new("RGB",(480,680),
                (60+int(theme*7)%130,90+edition*25,126+int(theme*4)%110))
            d=ImageDraw.Draw(picture)
            for j in range(10):
                x=j*51%420;y=j*66%600
                d.ellipse((x,y,x+63,y+99),outline=(224,194,151),width=5)
            self.images[key]=_jpeg(picture)
        return self.images[key]


class BrochureV3Tests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.photos=PhotoFixture()
        cls.product=FakeProduct("Custom tri-fold brochures","marketing-materials")
        cls.surface=PrintPage("Outside",11,8.5,11,8.5,(0,0,1,1))

    def test_only_trifold_in_marketing_materials(self):
        self.assertTrue(is_trifold(self.product))
        for name,category in (
            ("Custom Flyers","marketing-materials"),
            ("Premium Bi-Fold Brochures","marketing-materials"),
            ("Custom tri-fold brochures","promotional-products"),
            ("Custom Canopy Tent","marketing-materials"),
            ("Photo Calendar 2027","marketing-materials"),
            ("Premium Business Cards","marketing-materials"),
        ):
            self.assertFalse(is_trifold(FakeProduct(name,category)),name)

    def test_complete_count_roles_and_art_direction(self):
        self.assertEqual(COUNT,100)
        self.assertEqual(len(FEATURES),20)
        self.assertEqual(len(DIRECTIONS),5)
        self.assertEqual([art_direction(i) for i in range(5)],[0,1,2,3,4])
        self.assertEqual([_panel_role(0,i) for i in range(3)],
                         ["flap","back","cover"])
        self.assertEqual([_panel_role(1,i) for i in range(3)],
                         ["intro","offer","contact"])
        self.assertIn("luxury-v3",GENERATOR)

    def test_panels_are_inside_fold_safe_regions(self):
        w,h=canvas_size(self.surface)
        region=physical_region(self.product,self.surface,w,h)
        for i in range(3):
            x,y,pw,ph=_page_panel(self.surface,i,region)
            self.assertGreaterEqual(x,w*i/3)
            self.assertLessEqual(x+pw,w*(i+1)/3)
            self.assertGreater(pw,115)
            self.assertGreater(ph,360)

    def test_all_100_unique_and_editable_on_both_sides(self):
        signatures=set()
        for idx in range(100):
            pages=[
                build_page(self.product,idx,side,self.surface,self.photos)
                for side in (0,1)
            ]
            self.assertEqual([p["name"] for p in pages],["Outside","Inside"])
            for page in pages:
                self.assertEqual(page["foldPanelCount"],3)
                self.assertEqual(page["foldGuides"],[1/3,2/3])
                self.assertEqual(page["physical"]["unit"],"in")
                texts=[o for o in page["objects"] if o["type"]=="textbox"]
                photos=[o for o in page["objects"] if o["type"]=="image"]
                self.assertGreaterEqual(len(photos),3)
                # Outside: 11+ editable fields; inside: 9 purposeful
                # fields, avoiding overcrowding narrow folded panels.
                self.assertGreaterEqual(len(texts),9)
                self.assertTrue(all(o["customerEditable"] for o in texts+photos))
                self.assertTrue(all(o["manualReplacement"] for o in texts+photos))
                self.assertFalse(any(
                    "REPLACE PHOTO" in str(o.get("text","")).upper()
                    for o in texts
                ))
                self.assertTrue(all(
                    o["src"].startswith("data:image/jpeg;base64,") for o in photos
                ))
                # All editorial content stays within a physical panel,
                # except the single full-print substrate.
                for o in page["objects"]:
                    self.assertGreaterEqual(o["left"],0)
                    self.assertGreaterEqual(o["top"],0)
                    self.assertLessEqual(o["left"]+o["width"],page["width"]+.2)
                    self.assertLessEqual(o["top"]+o["height"],page["height"]+.2)
                    if o["name"]=="Editable continuous brochure substrate":
                        continue
                    panel=min(2,int((o["left"]+o["width"]/2)/(page["width"]/3)))
                    low=panel*page["width"]/3
                    high=(panel+1)*page["width"]/3
                    self.assertGreaterEqual(o["left"],low-.2)
                    self.assertLessEqual(o["left"]+o["width"],high+.2)
            signature=tuple(
                (o["type"],o["left"],o["top"],o.get("text"))
                for p in pages for o in p["objects"]
            )
            self.assertNotIn(signature,signatures)
            signatures.add(signature)
        self.assertEqual(len(signatures),100)

    def test_cover_first_gallery_is_real_artwork_not_photo_placeholders(self):
        for idx in (0,1,2,3,4,20,42,99):
            pages=[build_page(self.product,idx,side,self.surface,self.photos)
                   for side in (0,1)]
            out=_preview(pages)
            self.assertGreater(len(out),8000)
            with Image.open(io.BytesIO(out)) as preview:
                self.assertEqual(preview.format,"PNG")
                self.assertEqual(preview.size,(1000,1200))
                self.assertGreater(len(preview.getcolors(1000*1200) or []),20)
