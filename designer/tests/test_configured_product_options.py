from types import SimpleNamespace
from django.test import SimpleTestCase, RequestFactory
from designer.views import _product_option_groups, _selected_configured_variant


class ConfiguredProductOptionsTests(SimpleTestCase):
    def setUp(self):
        self.product = SimpleNamespace(source_attributes={
            'shape_variant_options': [{'name': 'Square', 'key': 'square'}, {'name': 'Round', 'key': 'circle'}],
            'material_variant_options': [{'name': 'Wood', 'key': 'wood'}],
        })

    def test_named_choices_use_stable_keys_without_exposing_metadata(self):
        groups = _product_option_groups(self.product, [], [])
        self.assertEqual([g['key'] for g in groups], ['shape', 'material'])
        self.assertEqual(groups[0]['choices'][0], {'name': 'Square', 'key': 'square'})

    def test_selection_validated_and_defaults_to_configured_choice(self):
        factory = RequestFactory()
        self.assertEqual(_selected_configured_variant(self.product, factory.get('/', {'shape': 'circle'}), 'shape'), 'circle')
        self.assertEqual(_selected_configured_variant(self.product, factory.get('/', {'shape': 'invalid'}), 'shape'), 'square')
        saved = SimpleNamespace(design_json={'_zenvibe_storefront': {'shape_key': 'circle'}})
        self.assertEqual(_selected_configured_variant(self.product, factory.get('/'), 'shape', saved), 'circle')
