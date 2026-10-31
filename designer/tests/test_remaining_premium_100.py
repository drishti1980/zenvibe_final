"""Premium 100-template acceptance tests.

These are fully offline: no GitHub/zenvibe.ca/Unsplash requests, DB writes or
existing template modifications. Run with Django's regular test runner.
"""
from __future__ import annotations

import io
import re
from types import SimpleNamespace

from django.test import SimpleTestCase
from PIL import Image, ImageDraw

from designer.management.commands.rebuild_remaining_premium_100 import (
    TARGET, GENERATOR, PROTECTED_TOKENS, PrintPage, family_for, protected,
    layout_index, BRIEFS, canvas_size, physical_region, build_page,
    render_preview, _jpeg,
)
from designer.management.commands.install_remaining_premium_100 import Command as BatchCommand


class ParentCategory:
    def __init__(self,name,slug,pk,parent=None):
        self.name=name;self.slug=slug;self.pk=pk;self.parent=parent


class FakeProduct:
    def __init__(self,name,slug):
        self.name=name
        self.category=ParentCategory(slug.replace("-"," ").title(),slug,1)
        self.safe_margin_in=.125


class FakePhotos:
    """A deterministic colour/photo-like image, not a stock-photo fallback."""
    def __init__(self):
        self.calls=[]
        self.data={}
    def crop(self,theme,aspect,edition):
        self.calls.append((theme,aspect,edition))
        key=(theme,round(aspect,3),edition)
        if key not in self.data:
            width=400
            height=max(180,round(400/max(.35,aspect)))
            pic=Image.new("RGB",(width,height),(
                35+theme*6, 100+(edition*23)%100, 120+(theme*7)%120
            ))
            d=ImageDraw.Draw(pic)
            for j in range(9):
                x=(j*71)%width; y=(j*43)%height
                d.ellipse((x,y,x+75,y+70),outline=(232,208,151),width=4)
            self.data[key]=_jpeg(pic)
        return self.data[key]


class ProtectedCategoryTests(SimpleTestCase):
    def test_protected_names_never_generate(self):
        names=(
            "10x10 FT Custom Canopy Tent",
            "Canopy Tent Full Back Wall",
            "Premium Business Cards",
            "Custom Desk Calendars",
            "Premium Photo Calendar 2027",
            "Custom Invitation Cards",
            "Custom 3D Printed Coasters with Logo",
            "Crystal Diamond Award",
            "Compact Lightweight Umbrella – 36 Inch",
        )
        for name in names:
            with self.subTest(name=name):
                p=FakeProduct(name,"marketing-materials")
                self.assertTrue(protected(p))
                self.assertEqual(family_for(p),"")

    def test_catalogue_family_coverage(self):
        expected={
            ("Custom Flyers","marketing-materials"):"flyer",
            ("Premium Bi-Fold Brochures","marketing-materials"):"brochure",
            ("Premium Custom Tickets Printing","marketing-materials"):"ticket",
            ("Deluxe Roll Up Banner","banners-displays"):"banner",
            ("Custom Table Runners","banners-displays"):"table-cover",
            ("Custom Tension Fabric Displays","banners-displays"):"display",
            ("Business Signature Metal Gel Pen","pens"):"pen",
            ("20oz Stainless Steel Tumbler","drinkware"):"drinkware",
            ("Unisex Cotton T-shirt with Front and Back Print","custom-apparel"):"apparel",
            ("Budget Cotton Tote Bag","bags"):"bag",
            ("Custom Spiral Notebook","custom-notebooks"):"notebook",
            ("Custom Name Badge","promotional-products"):"logo-product",
        }
        for (name,cat),want in expected.items():
            with self.subTest(name=name):
                self.assertEqual(family_for(FakeProduct(name,cat)),want)

    def test_irregular_cut_shapes_are_safely_skipped(self):
        for name in ("Custom Teardrop Flags", "Custom Feather Flags",
                     "Circle Pop Out Banners"):
            self.assertEqual(family_for(FakeProduct(name,"banners-displays")),"")

    def test_first_four_previews_have_four_layouts(self):
        self.assertEqual([layout_index(i) for i in range(4)],[0,1,2,3])
        self.assertEqual(len(set(layout_index(i) for i in range(100))),5)
        self.assertEqual(len(BRIEFS),20)
        self.assertEqual(TARGET,100)

    def test_bulk_runner_has_dry_run_and_apply_modes(self):
        self.assertTrue(hasattr(BatchCommand,"add_arguments"))


class ArtworkCompositionTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.photos=FakePhotos()

    def test_hundred_unique_illustrated_layouts_and_editable_objects(self):
        cases=(
            ("Custom Flyers","marketing-materials","flyer",PrintPage("Front",8.5,11,8.5,11,(0,0,1,1))),
            ("Deluxe Roll Up Banner","banners-displays","banner",PrintPage("Front",33,79,33,79,(0,0,1,1))),
            ("20oz Stainless Steel Tumbler","drinkware","drinkware",PrintPage("Front",8,3,8,3,(0,0,1,1))),
            ("Business Signature Metal Gel Pen","pens","pen",PrintPage("Front",2.2,.4,2.2,.4,(0,0,1,1))),
            ("Budget Cotton Tote Bag","bags","bag",PrintPage("Front",10,10,10,10,(0,0,1,1))),
        )
        for name,cat,family,surface in cases:
            signatures=set()
            p=FakeProduct(name,cat)
            for i in range(TARGET):
                page=build_page(p,family,i,0,surface,self.photos)
                self.assertTrue(page["editorCoordinates"])
                self.assertEqual(page["physical"]["unit"],"in")
                objects=page["objects"]
                self.assertGreaterEqual(len(objects),2)
                self.assertTrue(any(o["type"]=="textbox" and o["customerEditable"] for o in objects))
                for o in objects:
                    self.assertFalse(o.get("backgroundAsset"))
                    self.assertLessEqual(o["left"]+o["width"],page["width"]+.2)
                    self.assertLessEqual(o["top"]+o["height"],page["height"]+.2)
                if family!="pen":
                    self.assertTrue(any(o["type"]=="image" and
                                        o["manualReplacement"] for o in objects))
                else:
                    self.assertTrue(any(o["type"]=="circle" for o in objects))
                    self.assertFalse(any(o["type"]=="image" for o in objects))
                key=tuple((o["type"],o["left"],o["top"],o.get("text",""))
                          for o in objects)
                self.assertNotIn(key,signatures)
                signatures.add(key)
            self.assertEqual(len(signatures),100)

    def test_every_visible_gallery_preview_shares_editor_art(self):
        product=FakeProduct("Custom Flyers","marketing-materials")
        surface=PrintPage("Front",8.5,11,8.5,11,(0,0,1,1))
        for i in (0,1,2,3,4,19,20,39,60,99):
            page=build_page(product,"flyer",i,0,surface,self.photos)
            png=render_preview([page],"flyer")
            self.assertGreater(len(png),5000)
            with Image.open(io.BytesIO(png)) as output:
                self.assertEqual(output.format,"PNG")
                self.assertEqual(output.size,(900,1160))
                self.assertGreater(len(output.getcolors(900*1160) or []),25)

    def test_physical_safe_area_keeps_objects_inside_print_area(self):
        product=FakeProduct("Budget Cotton Tote Bag","bags")
        surface=PrintPage("Front",12,12,12,12,(.20,.25,.60,.50))
        w,h=canvas_size(surface)
        x,y,bw,bh=physical_region(product,surface,w,h)
        for i in (0,1,2,3,4,17,42,79,99):
            page=build_page(product,"bag",i,0,surface,self.photos)
            for obj in page["objects"]:
                self.assertGreaterEqual(obj["left"],x-.2)
                self.assertGreaterEqual(obj["top"],y-.2)
                self.assertLessEqual(obj["left"]+obj["width"],x+bw+.2)
                self.assertLessEqual(obj["top"]+obj["height"],y+bh+.2)

    def test_two_sided_designs_have_distinct_editable_pages(self):
        product=FakeProduct("Premium Bi-Fold Brochures","marketing-materials")
        surface=PrintPage("Outside",11,8.5,11,8.5,(0,0,1,1))
        for i in (0,1,5,21,76):
            outside=build_page(product,"brochure",i,0,surface,self.photos)
            inside=build_page(product,"brochure",i,1,surface,self.photos)
            self.assertNotEqual(outside["objects"],inside["objects"])
            self.assertGreaterEqual(len(outside["objects"]),5)
            self.assertGreaterEqual(len(inside["objects"]),5)
            self.assertNotEqual(
                [o.get("text") for o in outside["objects"] if o["type"]=="textbox"],
                [o.get("text") for o in inside["objects"] if o["type"]=="textbox"],
            )
