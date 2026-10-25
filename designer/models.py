from django.conf import settings
from django.db import models
from django.utils.text import slugify
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Leave blank for a main category. Select a category to make this a subcategory."
    )

    icon = models.CharField(max_length=20, default="✨")
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)
    is_out_of_stock = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "category"
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_parent(self):
        return self.parent_id is None

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name


class Product(models.Model):
    ORIENTATION_CHOICES = [("landscape", "Landscape"), ("portrait", "Portrait")]
    EDITOR_LAYOUT_CHOICES = [
        ("legacy", "Existing / legacy behaviour"),
        ("full_canvas", "Full canvas editable"),
        ("print_area", "Restricted print area"),
    ]
    CUSTOMIZER_CHOICES = [
        ("auto", "Automatic"),
        ("photo", "Product photo studio"),
        ("editor", "Layout editor"),
        ("tshirt", "Apparel studio"),
        ("pen", "Pen studio"),
        ("drinkware", "Drinkware studio"),
        ("awards", "Awards studio"),
        ("bags", "Bags studio"),
    ]
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=140)
    orientation = models.CharField(max_length=20, choices=ORIENTATION_CHOICES, default="landscape")
    customizer_mode = models.CharField(max_length=20, choices=CUSTOMIZER_CHOICES, default="auto", help_text="Choose a specific design studio, or leave Automatic for the existing product-based routing.")
    editor_layout_mode = models.CharField(max_length=20, choices=EDITOR_LAYOUT_CHOICES, default="legacy", help_text="Legacy preserves all existing template behaviour. New products can opt into full-canvas or restricted print-area mode.")
    workspace_width_in = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Outer editor workspace/ruler width in inches. Separate from printable width.")
    workspace_height_in = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Outer editor workspace/ruler height in inches. Separate from printable height.")
    constrain_to_print_area = models.BooleanField(default=False, help_text="Prevent customer-editable objects from leaving configured print areas.")
    show_product_reference = models.BooleanField(default=False, help_text="Show the product/mockup as a locked reference layer in the universal editor.")
    slug = models.SlugField(blank=True)
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True, help_text="Short product summary shown beside the product image.")
    product_information = models.TextField(blank=True, help_text="Additional/product information shown in the Information tab.")
    printing_method = models.TextField(blank=True, help_text="Product-specific printing/decorating method. Leave blank to hide the Printing Method tab.")
    design_guidelines = models.TextField(blank=True, help_text="Product-specific artwork/design guidelines. Leave blank to hide the Design Guidelines tab.")
    printing_guidelines = models.TextField(blank=True, help_text="Product-specific artwork and printing guidance.")
    faqs = models.TextField(blank=True, help_text="Product-specific FAQs. HTML is supported.")
    source_attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Optional product-specific storefront options. "
            'Example: {"Material": ["Matte", "Glossy"], "Printed Sides": ["Single Sided", "Double Sided"]}. '
            "Leave empty to hide additional options on the storefront."
        ),
    )
    price = models.DecimalField(max_digits=8, decimal_places=2, default=39.00)
    min_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Lowest current/source price for this product."
    )
    max_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Highest current/source price for this product."
    )
    minimum_quantity = models.PositiveIntegerField(default=1, help_text="Minimum quantity customers may order.")
    maximum_quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Optional maximum quantity customers may order. Leave blank for no maximum.")
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    editor_reference_image = models.ImageField(
        upload_to="products/editor_reference/",
        blank=True,
        null=True,
        help_text="Clean/blank product image used only as the locked reference in restricted print-area editor mode. Do not upload a promotional image with sample artwork baked in.",
    )
    hover_image = models.ImageField(upload_to="products/hover/", blank=True, null=True, help_text="Optional alternate image shown on hover.")
    # Internal editor/template coordinate system.
    # DO NOT use these as physical measurements.
    width = models.PositiveIntegerField(
        default=1050,
        help_text="Internal editor canvas width in pixels. Existing templates depend on this."
    )

    height = models.PositiveIntegerField(
        default=600,
        help_text="Internal editor canvas height in pixels. Existing templates depend on this."
    )

    # Real-world print dimensions used by ruler/export/print calculations.
    print_width_in = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Physical artwork width in inches. Example: 3.5 for a business card."
    )

    print_height_in = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Physical artwork height in inches. Example: 2.0 for a business card."
    )

    bleed_in = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("0.125"),
        help_text="Bleed in inches."
    )

    safe_margin_in = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("0.125"),
        help_text="Safe margin in inches."
    )

    min_dpi = models.PositiveIntegerField(default=300)
    bleed_mm = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    safe_margin_mm = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    # min_dpi = models.PositiveIntegerField(default=150)
    is_active = models.BooleanField(default=True)
    is_out_of_stock = models.BooleanField(default=False)
    is_on_sale = models.BooleanField(default=False, db_index=True)
    sale_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    sale_badge = models.CharField(max_length=40, default="Sale!", blank=True)
    sale_priority = models.PositiveIntegerField(default=100)
    # Defines the customer-editable zone as a % of the product photo's own size,
    # so it works at any image resolution and needs no code changes when a new
    # photo is uploaded. Left unset, the customizer falls back to a sensible
    # centered default box.
    print_left_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Left edge of the editable area, as % of photo width.")
    print_top_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Top edge of the editable area, as % of photo height.")
    print_width_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Width of the editable area, as % of photo width.")
    print_height_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Height of the editable area, as % of photo height.")

    class Meta:
        ordering = ["name"]
        unique_together = ("category", "slug")

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "product"
            candidate = base_slug
            suffix = 2
            qs = Product.objects.filter(category_id=self.category_id, slug=candidate)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.exists():
                candidate = f"{base_slug}-{suffix}"
                suffix += 1
                qs = Product.objects.filter(category_id=self.category_id, slug=candidate)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductSizeVariant(models.Model):
    """
    Product-specific size option used for product configuration and quantity pricing.
    The editor_profile value is a stable key that can be used by the frontend/editor
    to select a size-specific configuration without coupling it to the display name.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="size_variants",
    )
    name = models.CharField(max_length=140)
    size_key = models.SlugField(max_length=140)
    editor_profile = models.CharField(
        max_length=140,
        blank=True,
        help_text="Optional editor configuration/profile key for this size.",
    )
    print_width_in = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Physical width in inches for this size variant."
    )
    print_height_in = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="Physical height in inches for this size variant."
    )
    canvas_width = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Optional editor canvas width for this size variant."
    )
    canvas_height = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Optional editor canvas height for this size variant."
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size_key"],
                name="unique_product_size_key",
            )
        ]
        verbose_name = "Product size variant"
        verbose_name_plural = "Product size variants"

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class ProductColorVariant(models.Model):
    """Product-specific colour option shown to customers."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="color_variants",
    )
    name = models.CharField(max_length=120)
    color_key = models.SlugField(max_length=120)
    hex_value = models.CharField(
        max_length=9,
        blank=True,
        help_text="Hex colour value such as #FFFFFF.",
    )
    slug_suffix = models.SlugField(
        max_length=120,
        blank=True,
        help_text="Optional suffix used when building colour-specific URLs/slugs.",
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "color_key"],
                name="unique_product_color_key",
            )
        ]
        verbose_name = "Product color variant"
        verbose_name_plural = "Product color variants"

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class ProductPriceTier(models.Model):
    """
    Quantity-based unit pricing for a product.
    A tier may optionally target one ProductSizeVariant; leaving variant blank
    makes it a product-wide/default tier.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="price_tiers",
    )
    variant = models.ForeignKey(
        ProductSizeVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="price_tiers",
        help_text="Optional size variant. Leave blank for a product-wide tier.",
    )
    min_quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["min_quantity", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "variant", "min_quantity"],
                name="unique_product_variant_price_tier",
            )
        ]
        verbose_name = "Product price tier"
        verbose_name_plural = "Product price tiers"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.variant_id and self.product_id and self.variant.product_id != self.product_id:
            raise ValidationError({
                "variant": "Selected size variant must belong to this product."
            })

    def __str__(self):
        variant_name = self.variant.name if self.variant_id else "Default"
        return f"{self.product.name} — {variant_name} — {self.min_quantity}+ @ {self.unit_price}"


class ProductImage(models.Model):
    """Additional product photos, colours and angles.

    Each image can have its own printable area. If it is left unset, the
    product-level print area remains the fallback so older products keep
    working without any changes.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="angle_images")
    image = models.ImageField(upload_to="product_angles/")
    label = models.CharField(max_length=120, blank=True, help_text="Optional label such as Black, Front, Back or Side view.")
    sort_order = models.PositiveIntegerField(default=0)
    print_left_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    print_top_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    print_width_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    print_height_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]

    @property
    def has_custom_print_area(self):
        return self.print_left_pct is not None

    def __str__(self):
        return self.label or f"{self.product.name} — image {self.sort_order}"

class ProductPrintSurface(models.Model):
    """
    Defines individual editable pages / physical print surfaces for a product.

    Examples:
    - Business Card: Front, Back
    - Canopy: Canopy Top, Back Wall, Front Valance, Side Wall

    IMPORTANT:
    print_width_in / print_height_in are physical dimensions in inches.
    They DO NOT replace Product.width / Product.height.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="print_surfaces"
    )

    label = models.CharField(
        max_length=120,
        help_text="Example: Canopy Top, Back Wall, Front Valance"
    )

    print_width_in = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        help_text="Physical printable width in inches."
    )

    print_height_in = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        help_text="Physical printable height in inches."
    )

    workspace_width_in = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Optional outer ruler/workspace width for this surface. Falls back to the Product workspace.")
    workspace_height_in = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Optional outer ruler/workspace height for this surface. Falls back to the Product workspace.")

    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls the page/surface order in the editor."
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Product print surface"
        verbose_name_plural = "Product print surfaces"

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        errors = {}
        if self.print_width_in is None or self.print_width_in <= 0:
            errors["print_width_in"] = "Print width must be greater than 0 inches."
        if self.print_height_in is None or self.print_height_in <= 0:
            errors["print_height_in"] = "Print height must be greater than 0 inches."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.product.name} — {self.label}"

class ProductPrintArea(models.Model):
    """
    Allows multiple printable/customisable areas on each product image.

    product_image = NULL means the main Product.image.
    A ProductImage value means the area belongs only to that extra image.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="print_areas"
    )

    product_image = models.ForeignKey(
        ProductImage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="print_areas"
    )

    surface = models.ForeignKey(ProductPrintSurface, on_delete=models.CASCADE, null=True, blank=True, related_name="print_areas", help_text="Optional editor surface/page this print area belongs to.")

    name = models.CharField(
        max_length=100,
        default="Print Area"
    )

    left = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    top = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    width = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    height = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    print_width_in = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Physical printable width of this area in inches.")
    print_height_in = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Physical printable height of this area in inches.")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        image_name = (
            self.product_image.label
            if self.product_image
            else "Main image"
        )

        return f"{self.product.name} - {image_name} - {self.name}"


class DesignTemplate(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="templates")
    name = models.CharField(max_length=140)
    preview = models.ImageField(upload_to="template_previews/", blank=True, null=True)
    json_data = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name


class SavedDesign(models.Model):
    STATUS_CHOICES = [("draft", "Draft"), ("cart", "In cart"), ("ordered", "Ordered")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="zenvibe_designs")
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    source_template = models.ForeignKey(DesignTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="customer_designs")
    name = models.CharField(max_length=160, default="Untitled Design")
    design_json = models.JSONField(default=dict)
    preview_png = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)
    is_autosave = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class DesignVersion(models.Model):
    design = models.ForeignKey(SavedDesign, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    design_json = models.JSONField(default=dict)
    preview_png = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        unique_together = ("design", "version")

    def __str__(self):
        return f"{self.design.name} v{self.version}"

class Order(models.Model):
    STATUS_CHOICES = [
        ("new", "New"), ("confirmed", "Confirmed"), ("in_production", "In production"),
        ("shipped", "Shipped"), ("completed", "Completed"), ("cancelled", "Cancelled"),
    ]
    order_number = models.CharField(max_length=24, unique=True, blank=True)
    design = models.ForeignKey(SavedDesign, on_delete=models.PROTECT, related_name="orders")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="zenvibe_orders")
    customer_name = models.CharField(max_length=160)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=160, blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    province = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="new", db_index=True)
    PAYMENT_STATUS_CHOICES = [("pending", "Pending"), ("bypassed", "Bypassed / test"), ("paid", "Paid"), ("failed", "Failed"), ("refunded", "Refunded")]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending", db_index=True)
    payment_provider = models.CharField(max_length=30, default="bypass")
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    customer_notes = models.TextField(blank=True)
    coupon_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            self.order_number = "ZV-" + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number or f"Order {self.pk}"


class OrderWorkflowConfig(models.Model):
    PAYMENT_MODE_CHOICES = [("bypass", "Bypass / test mode"), ("stripe", "Stripe Checkout")]
    name = models.CharField(max_length=80, default="Default workflow")
    is_active = models.BooleanField(default=True)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default="bypass")
    currency = models.CharField(max_length=3, default="cad")
    admin_notification_emails = models.TextField(blank=True, help_text="Comma-separated admin notification email addresses")
    auto_confirm = models.BooleanField(default=True)
    confirm_after_minutes = models.PositiveIntegerField(default=0)
    auto_start_production = models.BooleanField(default=True)
    production_after_hours = models.PositiveIntegerField(default=24)
    auto_ship = models.BooleanField(default=False)
    ship_after_days = models.PositiveIntegerField(default=5)
    auto_complete = models.BooleanField(default=False)
    complete_after_days = models.PositiveIntegerField(default=10)
    email_customer_on_order = models.BooleanField(default=True)
    email_customer_on_status_change = models.BooleanField(default=True)
    email_admin_on_order = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order workflow configuration"
        verbose_name_plural = "Order workflow configuration"

    def __str__(self):
        return self.name

    @classmethod
    def current(cls):
        return cls.objects.filter(is_active=True).order_by("id").first() or cls.objects.create()


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    automatic = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_number}: {self.from_status} → {self.to_status}"

class ChatbotKnowledge(models.Model):
    category = models.CharField(max_length=80, default="General")
    question = models.CharField(max_length=240)
    answer = models.TextField()
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated keywords and phrases")
    sort_order = models.PositiveIntegerField(default=20)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "category", "question"]
        verbose_name = "Chatbot knowledge"
        verbose_name_plural = "Chatbot knowledge"

    def __str__(self):
        return self.question


class ChatInquiry(models.Model):
    STATUS_CHOICES = [("new", "New"), ("contacted", "Contacted"), ("closed", "Closed")]
    name = models.CharField(max_length=140, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new", db_index=True)
    page_url = models.CharField(max_length=500, blank=True)
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Chat inquiry"
        verbose_name_plural = "Chat inquiries"

    def __str__(self):
        return f"{self.name or self.email or 'Website visitor'} — {self.created_at:%Y-%m-%d}"

from django.urls import reverse
from django.utils import timezone


class BlogPost(models.Model):
    title = models.CharField(
        max_length=220
    )

    slug = models.SlugField(
        max_length=240,
        unique=True,
        blank=True
    )

    category = models.CharField(
        max_length=120,
        blank=True,
        default=""
    )

    author_name = models.CharField(
        max_length=120,
        blank=True,
        default="ZenVibe Team"
    )

    excerpt = models.TextField(
        blank=True
    )

    body = models.TextField(
        blank=True,
        help_text=(
            "Main article text. Existing articles can continue "
            "using this field."
        )
    )

    image = models.ImageField(
        upload_to="blog/",
        blank=True,
        null=True
    )

    image_alt = models.CharField(
        max_length=255,
        blank=True
    )

    is_published = models.BooleanField(
        default=True
    )

    allow_comments = models.BooleanField(
        default=True
    )

    published_at = models.DateTimeField(
        default=timezone.now
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    seo_title = models.CharField(
        max_length=220,
        blank=True
    )

    seo_description = models.CharField(
        max_length=320,
        blank=True
    )

    class Meta:
        ordering = [
            "-published_at",
            "-id"
        ]
        verbose_name = "Blog post"
        verbose_name_plural = "Blog posts"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:220]
            slug = base_slug
            number = 2

            while BlogPost.objects.filter(
                slug=slug
            ).exclude(pk=self.pk).exists():

                slug = f"{base_slug}-{number}"
                number += 1

            self.slug = slug

        if not self.image_alt:
            self.image_alt = self.title

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "designer:blog_detail",
            kwargs={"slug": self.slug}
        )

    @property
    def approved_comment_count(self):
        return self.comments.filter(
            is_approved=True
        ).count()


class BlogPostImage(models.Model):
    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="content_images"
    )

    image = models.ImageField(
        upload_to="blog/content/"
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True
    )

    caption = models.CharField(
        max_length=255,
        blank=True
    )

    sort_order = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        ordering = [
            "sort_order",
            "id"
        ]
        verbose_name = "Article image"
        verbose_name_plural = "Article images"

    def __str__(self):
        return f"{self.post.title} - image {self.pk}"


class BlogComment(models.Model):
    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    name = models.CharField(
        max_length=120
    )

    email = models.EmailField()

    website = models.URLField(
        blank=True
    )

    comment = models.TextField(
        max_length=4000
    )

    is_approved = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "created_at"
        ]
        verbose_name = "Blog comment"
        verbose_name_plural = "Blog comments"

    def __str__(self):
        return f"{self.name} - {self.post.title}"


class Testimonial(models.Model):
    customer_name = models.CharField(max_length=160)
    company = models.CharField(max_length=160, blank=True)
    review = models.TextField(max_length=1200)
    rating = models.PositiveSmallIntegerField(default=5)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-created_at", "id"]

    def __str__(self):
        return self.customer_name


class BrandLogo(models.Model):
    name = models.CharField(max_length=160)
    image = models.ImageField(upload_to="home/brand-logos/")
    website_url = models.URLField(max_length=500, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name", "id"]

    def __str__(self):
        return self.name


class HomeBanner(models.Model):
    title = models.CharField(max_length=180, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="home/banners/")
    mobile_image = models.ImageField(upload_to="home/banners/mobile/", blank=True, null=True)
    button_text = models.CharField(max_length=80, blank=True, default="Shop Now")
    button_url = models.CharField(
        max_length=500, blank=True,
        help_text="Use a site path such as /shop/ or a full https:// URL."
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Home page banner"
        verbose_name_plural = "Home page banners"

    def __str__(self):
        return self.title or f"Home banner {self.pk or ''}".strip()


class PageContentBlock(models.Model):
    PAGE_CHOICES = [
        ("home", "Home Page"),
        ("about", "About Us"),
        ("our_work", "Our Work"),
        ("contact", "Contact"),
    ]
    page = models.CharField(max_length=20, choices=PAGE_CHOICES, db_index=True)
    section_key = models.SlugField(
        max_length=80,
        help_text="Stable section identifier, e.g. welcome, story, mission."
    )
    heading = models.CharField(max_length=200, blank=True)
    subheading = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to="page-content/", blank=True, null=True)
    button_text = models.CharField(max_length=80, blank=True)
    button_url = models.CharField(max_length=500, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["page", "section_key"],
                name="unique_page_content_section"
            )
        ]
        verbose_name = "Page content block"
        verbose_name_plural = "Page content blocks"

    def __str__(self):
        return f"{self.get_page_display()} — {self.heading or self.section_key}"
    
    
    # ============================================================
# GLOBAL SITE SETTINGS
# ============================================================

class SiteSettings(models.Model):
    """
    Global ZenVibe website information.

    Used throughout:
    - About Us
    - Contact Us
    - Header
    - Footer
    """

    site_name = models.CharField(
        max_length=150,
        default="ZenVibe Corporate Gifts"
    )

    email = models.EmailField(
        blank=True,
        default="info@zenvibe.ca"
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
        default="+1 (587) 340-2358"
    )

    address = models.CharField(
        max_length=255,
        blank=True,
        default="4003 98 St NW Unit 72, Edmonton, AB T6E 6M8"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.site_name or "Site Settings"

    @property
    def phone_href(self):
        """Return phone number suitable for tel: links."""

        if not self.phone:
            return ""

        value = self.phone.strip()

        if value.startswith("+"):
            return "+" + "".join(
                char for char in value[1:]
                if char.isdigit()
            )

        return "".join(
            char for char in value
            if char.isdigit()
        )

    @property
    def maps_url(self):
        """Return clickable Google Maps URL."""

        if not self.address:
            return ""

        from urllib.parse import quote_plus

        return (
            "https://www.google.com/maps/search/"
            "?api=1&query="
            + quote_plus(self.address)
        )

    @classmethod
    def get_settings(cls):
        """
        Return the one global SiteSettings object.
        Automatically create it if it doesn't exist.
        """

        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "site_name": "ZenVibe Corporate Gifts",
                "email": "info@zenvibe.ca",
                "phone": "+1 (587) 340-2358",
                "address": (
                    "4003 98 St NW Unit 72, "
                    "Edmonton, AB T6E 6M8"
                ),
            }
        )

        return obj


# Customer-owned reusable Canadian shipping/billing addresses.
from .customer_models import CustomerAddress


class StoreEmailAccount(models.Model):
    PROVIDERS = [("gmail", "Gmail / Google Workspace"), ("outlook", "Outlook / Microsoft 365")]
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    email_address = models.EmailField(unique=True)
    encrypted_app_password = models.TextField(blank=True, default="", editable=False)
    ms_tenant_id = models.CharField(max_length=255, blank=True, default="")
    ms_client_id = models.CharField(max_length=255, blank=True, default="")
    encrypted_ms_client_secret = models.TextField(blank=True, default="", editable=False)
    is_active = models.BooleanField(default=False)
    notify_on_order = models.BooleanField(default=True)
    notify_on_contact = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store email account"
        verbose_name_plural = "Email configuration"
        constraints = [models.UniqueConstraint(fields=["is_active"], condition=models.Q(is_active=True), name="zv_single_active_mailbox")]

    def __str__(self):
        return self.email_address

class StoreEmailTemplate(models.Model):
    EVENT_CHOICES = [
        ("order_customer", "Customer order confirmation"),
        ("order_admin", "New order notification to staff"),
        ("order_status", "Customer order status update"),
        ("contact_admin", "Contact Us notification to staff"),
    ]
    event = models.CharField(max_length=40, choices=EVENT_CHOICES, unique=True)
    subject = models.CharField(max_length=250)
    body = models.TextField(help_text="Available placeholders: {customer_name}, {order_number}, {product_name}, {quantity}, {total}, {status}, {old_status}, {customer_email}, {subject}, {message}, {phone}, {product_category}.")
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Store email template"
        verbose_name_plural = "Email templates"

    def __str__(self):
        return self.get_event_display()

class DiscountCoupon(models.Model):
    products = models.ManyToManyField(
        "Product", related_name="discount_coupons",
        help_text="This code applies only to these products. Select at least one product.",
    )
    DISCOUNT_TYPES = [("percent", "Percentage"), ("fixed", "Fixed CAD amount")]
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default="percent")
    value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    show_at_checkout = models.BooleanField(default=True)

    class Meta:
        ordering = ["title", "code"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.value is not None and (self.value < 0 or (self.discount_type == "percent" and self.value > 100)):
            raise ValidationError({"value": "Enter a non-negative discount; percentage discounts cannot exceed 100."})

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper().lstrip("#")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class PaymentSetup(OrderWorkflowConfig):
    """Admin-only alias: payment settings retain the existing workflow data."""

    class Meta:
        proxy = True
        verbose_name = "Payment setup"
        verbose_name_plural = "Payment setup"
