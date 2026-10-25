
# Generated manually for demo stability
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(blank=True, unique=True)),
                ('icon', models.CharField(default='✨', max_length=20)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='categories/')),
                ('is_active', models.BooleanField(default=True)),
                ('is_out_of_stock', models.BooleanField(default=False)),
                ('sort_order', models.PositiveIntegerField(default=10)),
            ],
            options={'ordering': ['sort_order', 'name']},
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=140)),
                ('slug', models.SlugField(blank=True)),
                ('description', models.TextField(blank=True)),
                ('price', models.DecimalField(decimal_places=2, default=39.0, max_digits=8)),
                ('image', models.ImageField(blank=True, null=True, upload_to='products/')),
                ('width', models.PositiveIntegerField(default=1050)),
                ('height', models.PositiveIntegerField(default=600)),
                ('is_active', models.BooleanField(default=True)),
                ('is_out_of_stock', models.BooleanField(default=False)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='designer.category')),
            ],
            options={'ordering': ['name'], 'unique_together': {('category', 'slug')}},
        ),
        migrations.CreateModel(
            name='DesignTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=140)),
                ('preview', models.ImageField(blank=True, null=True, upload_to='template_previews/')),
                ('json_data', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='templates', to='designer.product')),
            ],
        ),
        migrations.CreateModel(
            name='SavedDesign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Untitled Design', max_length=160)),
                ('design_json', models.JSONField(default=dict)),
                ('preview_png', models.TextField(blank=True)),
                ('quantity', models.PositiveIntegerField(default=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='designer.product')),
            ],
        ),
    ]
