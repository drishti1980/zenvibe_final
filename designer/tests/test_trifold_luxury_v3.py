"""Tri-fold luxury V3 offline regression checks.

These tests use generated local photo-like pixels only for geometry testing.
The real installer uses curated licensed photo assets and fails safely if its
photography is unavailable. Tests never access Zenvibe.ca or modify the DB.
"""
import copy
import io
import re
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.core.management.base import CommandError
from PIL import Image, ImageDraw

from designer.management.commands.rebuild_remaining_premium_100 import (
    PrintPage, _jpeg, canvas_size, physical_region,
)
from designer.management.commands.rebuild_trifold_luxury_v3 import (
    GENERATOR, COUNT, DIRECTIONS, FEATURES, _page_panel, _panel_role,
    _existing, _preview, build_page, is_trifold, art_direction,
    _sheet_pair, _previous_sheet_dimensions, _missing_admin_sheet,
    resolve_trifold_pages, refresh_published_previews,
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


class GalleryEditorParityTests(SimpleTestCase):
    def test_thumbnail_shows_whole_outside_and_inside_pages_not_cropped_cover(self):
        pages=[
            {"name":"Outside","width":1200,"height":900},
            {"name":"Inside","width":1200,"height":900},
        ]
        render_calls=[]
        def fake_render(page,scale):
            render_calls.append((page["name"],scale))
            shade=(190,38,54,255) if page["name"]=="Outside" else (30,107,178,255)
            return Image.new("RGBA",(
                max(1,round(page["width"]*scale)),
                max(1,round(page["height"]*scale)),
            ),shade)
        with patch(
            "designer.management.commands.rebuild_trifold_luxury_v3._page_image",
            side_effect=fake_render,
        ):
            preview=_preview(pages)
        with Image.open(io.BytesIO(preview)) as result:
            self.assertEqual(result.size,(1000,1200))
            self.assertEqual(result.convert("RGB").getpixel((500,400)),(190,38,54))
            self.assertEqual(result.convert("RGB").getpixel((500,900)),(30,107,178))
        self.assertEqual([x[0] for x in render_calls],["Outside","Inside"])

    def test_preview_refresh_preserves_all_published_master_json_and_ids(self):
        class FakeRow:
            def __init__(self,index):
                self.pk=50000+index
                self.name="ZV Tri-Fold %03d"%(index+1)
                self.is_active=True
                self.json_data={
                    "generator":GENERATOR,
                    "pages":[
                        {"name":"Outside","width":1200,"height":900,
                         "objects":[{"type":"textbox","text":"Front"}]},
                        {"name":"Inside","width":1200,"height":900,
                         "objects":[{"type":"textbox","text":"Back"}]},
                    ],
                }
                self.preview=SimpleNamespace(
                    name="before.png",
                    storage=SimpleNamespace(exists=lambda path:True),
                )
                self.saved=[]
            def save(self,**kwargs):
                self.saved.append(kwargs)
        originals=[FakeRow(i) for i in range(COUNT)]
        mapping={idx:row for idx,row in enumerate(originals)}
        original_data=[copy.deepcopy(row.json_data) for row in originals]
        original_ids=[row.pk for row in originals]
        product=SimpleNamespace(pk=345)
        with patch(
            "designer.management.commands.rebuild_trifold_luxury_v3._preview",
            return_value=b"P"*10001,
        ),patch(
            "designer.management.commands.rebuild_trifold_luxury_v3._backup",
            return_value="trifold-before-backup.gz",
        ),patch(
            "designer.management.commands.rebuild_trifold_luxury_v3.transaction.atomic",
            side_effect=lambda:nullcontext(),
        ):
            updated=refresh_published_previews(product,originals,mapping)
        self.assertEqual(updated,100)
        self.assertEqual([row.pk for row in originals],original_ids)
        self.assertEqual([row.json_data for row in originals],original_data)
        self.assertTrue(all(row.is_active for row in originals))
        self.assertTrue(all(
            row.saved==[{"update_fields":["preview","updated_at"]}]
            for row in originals
        ))
        self.assertTrue(all(
            row.preview.name.startswith("template_previews/trifold-exact-v3-345-")
            for row in originals
        ))


class MissingAdminSheetTests(SimpleTestCase):
    """Product #345 can have valid generated masters but missing Admin inches."""

    @staticmethod
    def product(variants=(), has_surfaces=False):
        return SimpleNamespace(
            pk=345,
            print_surfaces=SimpleNamespace(filter=lambda **kw:
                SimpleNamespace(exists=lambda:has_surfaces)),
            size_variants=SimpleNamespace(filter=lambda **kw:variants),
            print_areas=SimpleNamespace(order_by=lambda *args:[]),
            workspace_width_in=None,
            workspace_height_in=None,
        )

    @staticmethod
    def previous(width=11,height=8.5,count=3):
        return [
            SimpleNamespace(
                is_active=True, pk=i,
                json_data={
                    "generator":"zenvibe-trifold-brochure-v1-json-svg",
                    "document":{"physical":{"widthIn":width,"heightIn":height}},
                },
            ) for i in range(1,count+1)
        ]

    def test_recovers_exact_existing_master_inches_not_pixel_canvas(self):
        originals=self.previous()
        self.assertEqual(_previous_sheet_dimensions(originals),(11.0,8.5))
        warnings=[]
        with patch(
            "designer.management.commands.rebuild_trifold_luxury_v3.configured_pages",
            side_effect=CommandError("Admin print width/height missing for page 1"),
        ):
            pages=resolve_trifold_pages(self.product(),originals,log=warnings.append)
        self.assertEqual(len(pages),2)
        self.assertEqual([p.label for p in pages],["Outside","Inside"])
        self.assertEqual([(p.width_in,p.height_in) for p in pages],
                         [(11.0,8.5),(11.0,8.5)])
        self.assertTrue(any("CONFIRM WITH PRINTER" in w for w in warnings))

    def test_explicit_size_variant_used_if_historical_metadata_absent(self):
        variant=SimpleNamespace(name="Standard",
                                print_width_in=11,print_height_in=8.5)
        with patch(
            "designer.management.commands.rebuild_trifold_luxury_v3.configured_pages",
            side_effect=CommandError("Admin print width/height missing for page 1"),
        ):
            pages=resolve_trifold_pages(self.product([variant]),[])
        self.assertEqual(pages[0].width_in,11)
        self.assertEqual(pages[1].height_in,8.5)

    def test_missing_all_sources_fails_with_actionable_message(self):
        with patch(
            "designer.management.commands.rebuild_trifold_luxury_v3.configured_pages",
            side_effect=CommandError("Admin print width/height missing for page 1"),
        ):
            with self.assertRaisesRegex(CommandError,"--sheet-width-in"):
                resolve_trifold_pages(self.product(),[])

    def test_legacy_inconsistency_or_variant_conflict_is_not_guessed(self):
        originals=self.previous(11,8.5)+self.previous(12,9)
        with self.assertRaisesRegex(CommandError,"disagree"):
            _previous_sheet_dimensions(originals)
        different=SimpleNamespace(name="Different size",
                                  print_width_in=12,print_height_in=9)
        with self.assertRaisesRegex(CommandError,"conflicts"):
            _missing_admin_sheet(self.product([different]),
                                 self.previous(11,8.5))

    def test_user_supplied_inches_work_when_no_legacy_metadata(self):
        with patch(
            "designer.management.commands.rebuild_trifold_luxury_v3.configured_pages",
            side_effect=CommandError("Admin print width/height missing for page 1"),
        ):
            pages=resolve_trifold_pages(self.product(),[],override=(11,8.5))
        self.assertEqual((pages[0].width_in,pages[0].height_in),(11.0,8.5))
        with self.assertRaisesRegex(CommandError,"BOTH"):
            resolve_trifold_pages(self.product(),[],override=(11,None))
        self.assertIsNone(_sheet_pair(0,8.5))
        self.assertIsNone(_sheet_pair(8.5,11))

    def test_partially_configured_admin_surface_is_not_overwritten(self):
        with patch(
            "designer.management.commands.rebuild_trifold_luxury_v3.configured_pages",
            side_effect=CommandError("Admin print width/height missing for page 1"),
        ):
            with self.assertRaisesRegex(CommandError,"specific surface"):
                resolve_trifold_pages(
                    self.product(has_surfaces=True),self.previous(),
                )

    def test_admin_dimensions_take_priority(self):
        faces=[
            PrintPage("Outside",12,9,12,9,(0,0,1,1)),
            PrintPage("Inside",12,9,12,9,(0,0,1,1)),
        ]
        with patch(
            "designer.management.commands.rebuild_trifold_luxury_v3.configured_pages",
            return_value=faces,
        ):
            pages=resolve_trifold_pages(self.product(),self.previous())
        self.assertEqual(pages,faces)


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

    def test_exact_sheet_gallery_is_real_artwork_not_photo_placeholders(self):
        for idx in (0,1,2,3,4,20,42,99):
            pages=[build_page(self.product,idx,side,self.surface,self.photos)
                   for side in (0,1)]
            out=_preview(pages)
            self.assertGreater(len(out),8000)
            with Image.open(io.BytesIO(out)) as preview:
                self.assertEqual(preview.format,"PNG")
                self.assertEqual(preview.size,(1000,1200))
                self.assertGreater(len(preview.getcolors(1000*1200) or []),20)
