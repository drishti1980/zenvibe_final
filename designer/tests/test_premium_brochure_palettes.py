"""Offline QA for the 100 non-repeating bi-/tri-fold luxury colourways.

No database, network, photo downloads or media writes. These assertions catch
the previous palette bug (5 repeating backgrounds; 20 repeating accents), poor
CTA foregrounds, and hardcoded repeated colours on inside panels.
"""
from django.test import SimpleTestCase

from designer.management.commands.premium_brochure_palettes import (
    palette_for, palette_signatures, validate_100_palettes, contrast,
)
from designer.management.commands.rebuild_premium_marketing_print_v2 import (
    make_marketing_page,
)
from designer.management.commands.rebuild_trifold_luxury_v3 import build_page
from designer.management.commands.rebuild_remaining_premium_100 import PrintPage
from designer.tests.test_remaining_premium_100 import FakeProduct, FakePhotos


class BrochureColorEngineTests(SimpleTestCase):
    def test_100_distinct_cover_backgrounds_and_100_distinct_foil_accents(self):
        for family in ("bifold", "trifold"):
            with self.subTest(family=family):
                self.assertTrue(validate_100_palettes(family))
                combos=palette_signatures(family)
                self.assertEqual(len(combos),100)
                self.assertEqual(len(set(combos)),100)
                self.assertEqual(len({p for p,a in combos}),100)
                self.assertEqual(len({a for p,a in combos}),100)
                self.assertNotEqual(combos[0],combos[5])
                self.assertNotEqual(combos[0],combos[20])
                self.assertNotEqual(combos[0],combos[80])

    def test_adjacent_palette_brightness_and_hue_are_not_near_duplicates(self):
        # A colour technically differs by one channel but still looks
        # identical. Golden-angle hue + alternating tone prevents that.
        for family in ("bifold","trifold"):
            combos=palette_signatures(family)
            for i in range(1,100):
                with self.subTest(family=family,number=i+1):
                    self.assertGreater(
                        contrast(combos[i][0],combos[i-1][0]),1.23
                    )

    def test_text_and_ctas_are_readable_on_all_100_and_all_six_panel_roles(self):
        for family in ("bifold","trifold"):
            for index in range(100):
                for role in (
                    "cover","back","flap","intro","offer","contact",
                    "story","services",
                ):
                    colors=palette_for(index,family,role)
                    with self.subTest(family=family,index=index,role=role):
                        self.assertGreaterEqual(
                            contrast(colors.ink,colors.paper),4.5
                        )
                        self.assertGreaterEqual(
                            contrast(colors.muted,colors.paper),4.5
                        )
                        self.assertGreaterEqual(
                            contrast(colors.on_accent,colors.accent),4.5
                        )

    def test_families_have_independent_palettes(self):
        bi=palette_signatures("bifold")
        tri=palette_signatures("trifold")
        self.assertNotEqual(bi,tri)
        self.assertEqual(len(bi),100)
        self.assertEqual(len(tri),100)


class BrochureColorArtworkTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.photos=FakePhotos()
        cls.bi=FakeProduct("Premium Bi-Fold Brochures","marketing-materials")
        cls.tri=FakeProduct("Custom tri-fold brochures","marketing-materials")
        cls.stock=PrintPage("Outside",11,8.5,11,8.5,(0,0,1,1))

    def test_bifold_actual_cover_colours_are_unique_in_fabric_artwork(self):
        found=set()
        for index in range(100):
            # Page 1 right-hand panel = physical front cover.
            page=make_marketing_page(
                self.bi,"bifold",index,0,self.stock,self.photos
            )
            paper=next(
                o["fill"] for o in page["objects"]
                if o["name"]=="Editable panel paper" and
                o["left"]>page["width"]/2
            )
            intended=palette_for(index,"bifold","cover").paper
            self.assertEqual(paper,intended)
            found.add(paper)
        self.assertEqual(len(found),100)

    def test_trifold_actual_front_cover_colours_are_unique_in_fabric_artwork(self):
        found=set()
        for index in range(100):
            # Rightmost panel on page 1 = physical front cover.
            page=build_page(self.tri,index,0,self.stock,self.photos)
            paper=next(
                o["fill"] for o in page["objects"]
                if o["name"]=="Editable luxury paper" and
                o["left"]>page["width"]*2/3
            )
            self.assertEqual(paper,palette_for(index,"trifold","cover").paper)
            self.assertEqual(
                page["paletteColors"]["paper"],
                palette_for(index,"trifold","cover").paper
            )
            found.add(paper)
        self.assertEqual(len(found),100)
