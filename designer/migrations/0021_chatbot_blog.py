from django.db import migrations, models
from django.utils import timezone
from django.utils.text import slugify


def seed_content(apps, schema_editor):
    K = apps.get_model('designer', 'ChatbotKnowledge')
    defaults = [
        ('Products','What products can I customize?','You can customize banners & displays, apparel, awards, promotional products, corporate gift sets, drinkware, notebooks, bags, marketing materials and pens.','products,categories,customize,customise'),
        ('Design','Can I upload my own logo or artwork?','Yes. Open a product customizer and use Uploads to add your logo, artwork or photo. You can then scale, rotate, crop and position it inside the printable area.','logo,artwork,upload,design,file'),
        ('Design','Do I get a proof before production?','Yes. ZenVibe provides an instant design preview and a final proof review before production.','proof,preview,approval,production'),
        ('Orders','How do I track my order?','Use My Orders when signed in, or ask us with your ZenVibe order number. Most custom orders require production time before shipping.','track,order,status,shipping'),
        ('Pricing','Do you offer bulk pricing?','Yes. Bulk pricing is available for business, event, team and organization orders. Contact ZenVibe for larger quantities or a custom quote.','bulk,discount,quantity,quote,pricing'),
        ('Shipping','Do you ship across Canada?','Yes. ZenVibe serves customers across Canada. Shipping timing depends on the product, customization method and production schedule.','shipping,delivery,canada'),
        ('Support','How can I contact ZenVibe?','Email info@zenvibe.ca or call (587) 340-2358. You can also leave your details here and the team can follow up.','contact,email,phone,help,support'),
    ]
    for cat,q,a,k in defaults:
        K.objects.get_or_create(question=q, defaults={'category':cat,'answer':a,'keywords':k})

    B = apps.get_model('designer','BlogPost')
    posts = [
        ('Real Estate Promotional Products Canada: 7 Must-Have Marketing Tools for Realtors in 2026','Corporate Gift Set, Marketing materials, Promotional Products','Practical branded marketing tools for Canadian real estate professionals, from signs and business cards to pens, notebooks and drinkware.'),
        ('How Custom Apparel Builds Brand Recognition for Small Businesses','Apparel','How consistent branded apparel can help small businesses create a professional, recognizable presence.'),
        ('Restaurant Marketing Ideas Using Custom Printed Products (2026 Guide)','Marketing materials, Promotional Products','Ideas for using menus, signs, apparel, drinkware and promotional items to strengthen restaurant branding.'),
        ('Custom Employee Welcome Kits in Canada: Everything You Need for New Hire Onboarding','Corporate Gift Set','A practical guide to building branded welcome kits for employees and new hires.'),
        ('Complete Event Branding Checklist for Canadian Businesses','Banners & Displays','A checklist for building a coordinated event presence with displays, apparel and promotional products.'),
        ('Custom Feather Flags Canada: The Complete Guide for Events, Storefronts & Trade Shows','Banners & Displays','A guide to using custom feather flags for visibility at storefronts, events and trade shows.'),
    ]
    now = timezone.now()
    for i,(t,c,e) in enumerate(posts):
        B.objects.get_or_create(slug=slugify(t), defaults={'title':t,'category':c,'excerpt':e,'body':e,'is_published':True,'published_at':now-timezone.timedelta(days=i*5)})

class Migration(migrations.Migration):
    dependencies = [('designer','0020_order_workflow_and_payments')]
    operations = [
        migrations.CreateModel(name='ChatbotKnowledge', fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('category',models.CharField(default='General',max_length=80)),('question',models.CharField(max_length=240)),('answer',models.TextField()),('keywords',models.CharField(blank=True,help_text='Comma-separated keywords and phrases',max_length=500)),('sort_order',models.PositiveIntegerField(default=20)),('is_active',models.BooleanField(default=True)),('updated_at',models.DateTimeField(auto_now=True))], options={'ordering':['sort_order','category','question'],'verbose_name':'Chatbot knowledge','verbose_name_plural':'Chatbot knowledge'}),
        migrations.CreateModel(name='ChatInquiry', fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('name',models.CharField(blank=True,max_length=140)),('email',models.EmailField(blank=True,max_length=254)),('phone',models.CharField(blank=True,max_length=40)),('message',models.TextField()),('status',models.CharField(choices=[('new','New'),('contacted','Contacted'),('closed','Closed')],db_index=True,default='new',max_length=20)),('page_url',models.CharField(blank=True,max_length=500)),('session_key',models.CharField(blank=True,db_index=True,max_length=40)),('created_at',models.DateTimeField(auto_now_add=True))], options={'ordering':['-created_at'],'verbose_name':'Chat inquiry','verbose_name_plural':'Chat inquiries'}),
        migrations.CreateModel(name='BlogPost', fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('title',models.CharField(max_length=220)),('slug',models.SlugField(blank=True,unique=True)),('excerpt',models.TextField(blank=True)),('body',models.TextField(blank=True)),('category',models.CharField(blank=True,max_length=100)),('image',models.ImageField(blank=True,null=True,upload_to='blog/')),('is_published',models.BooleanField(default=True)),('published_at',models.DateTimeField(blank=True,null=True)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True))], options={'ordering':['-published_at','-created_at']}),
        migrations.RunPython(seed_content, migrations.RunPython.noop),
    ]
