import json
from django.contrib import admin
from django import forms
from django.db.models import Q
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    Category,
    Product,
    ProductImage,
    DesignTemplate,
    SavedDesign,
    Order,
    OrderWorkflowConfig,
    OrderStatusHistory,
    ChatbotKnowledge,
    ChatInquiry,
    BlogPost,
    BlogPostImage,
    BlogComment,
    ProductSizeVariant, ProductColorVariant, ProductPriceTier, ProductPrintSurface, ProductPrintArea, HomeBanner, PageContentBlock,
    Testimonial, BrandLogo, SiteSettings,
)
from .services.template_geometry import snapshot_product_geometry, migrate_product_templates


admin.site.site_header = "ZenVibe Corporate Gifts Admin"
admin.site.site_title = "ZenVibe Admin"
admin.site.index_title = "Dashboard"


class TopLevelParentFilter(admin.SimpleListFilter):
    title = "parent category"
    parameter_name = "parent_group"

    def lookups(self, request, model_admin):
        parents = Category.objects.filter(
            parent__isnull=True,
            children__isnull=False,
        ).distinct().order_by("sort_order", "name")
        return [(str(item.pk), item.name) for item in parents]

    def queryset(self, request, queryset):
        value = self.value()
        return queryset.filter(parent_id=value) if value else queryset


class ProductCategoryGroupFilter(admin.SimpleListFilter):
    """Short, useful product filter: parent selection includes its children."""
    title = "category group"
    parameter_name = "category_group"

    def lookups(self, request, model_admin):
        return [
            (str(item.pk), item.name)
            for item in Category.objects.filter(parent__isnull=True).order_by("sort_order", "name")
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(Q(category_id=value) | Q(category__parent_id=value))


class ProductSubcategoryFilter(admin.SimpleListFilter):
    title = "subcategory"
    parameter_name = "subcategory"

    def lookups(self, request, model_admin):
        children = Category.objects.filter(parent__isnull=False)
        parent = request.GET.get("category_group")
        if parent:
            children = children.filter(parent_id=parent)
        return [(str(item.pk), f"{item.parent.name} → {item.name}")
                for item in children.select_related("parent").order_by("parent__sort_order", "sort_order", "name")]

    def queryset(self, request, queryset):
        return queryset.filter(category_id=self.value()) if self.value() else queryset


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image_preview", "image", "label", "sort_order", "print_area_status")
    readonly_fields = ("image_preview", "print_area_status")

    def image_preview(self, obj):
        if obj and obj.pk and obj.image:
            return format_html(
                '<img src="{}" alt="" style="width:74px;height:74px;object-fit:contain;border:1px solid #e4e8ef;border-radius:8px;background:#fff;padding:4px">',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "Preview"

    def print_area_status(self, obj):
        if not obj or not obj.pk:
            return "Set after saving"
        return "Custom" if obj.print_left_pct is not None else "Uses product default"
    print_area_status.short_description = "Print area"


class ProductSizeVariantInline(admin.TabularInline):
    model = ProductSizeVariant
    extra = 1
    fields = ("name", "size_key", "editor_profile", "print_width_in", "print_height_in", "canvas_width", "canvas_height", "is_active", "sort_order")


class ProductPrintSurfaceInline(admin.TabularInline):
    model = ProductPrintSurface
    extra = 0
    fields = ("label", "workspace_width_in", "workspace_height_in", "print_width_in", "print_height_in", "sort_order", "is_active")
    ordering = ("sort_order", "id")
    verbose_name = "Print surface (inches)"
    verbose_name_plural = "Print pages / surfaces — inches"


class ProductPrintAreaInline(admin.TabularInline):
    model = ProductPrintArea
    extra = 0
    fields = ("name", "surface", "product_image", "left", "top", "width", "height", "print_width_in", "print_height_in", "sort_order")
    ordering = ("sort_order", "id")
    verbose_name = "Restricted print area"
    verbose_name_plural = "Restricted print areas — percentage position + physical size"


class ProductColorVariantInline(admin.TabularInline):
    model = ProductColorVariant
    extra = 1
    fields = ("name", "color_key", "hex_value", "slug_suffix", "is_active", "sort_order")


class ProductPriceTierInline(admin.TabularInline):
    model = ProductPriceTier
    extra = 1
    fields = ("variant", "min_quantity", "unit_price", "is_active")
    ordering = ("variant", "min_quantity")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "parent",
        "is_active",
        "is_out_of_stock",
        "sort_order"
    )
    list_filter = (TopLevelParentFilter, "is_active", "is_out_of_stock")
    search_fields = ("name", "parent__name")
    actions = ("activate_categories", "deactivate_categories")

    prepopulated_fields = {
        "slug": ("name",)
    }

    @admin.action(description="Activate selected categories")
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} categor{'y' if updated == 1 else 'ies'} activated.")

    @admin.action(description="Deactivate selected categories")
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} categor{'y' if updated == 1 else 'ies'} deactivated.")



class ProductAdminForm(forms.ModelForm):
    """
    Friendly per-product delivery settings without changing the Product schema.
    Values are persisted inside the existing Product.source_attributes JSON.
    """
    show_customize_button = forms.BooleanField(
        required=False,
        initial=True,
        label="Show Customize button",
        help_text="Uncheck only after confirming Zenvibe.ca has no customization option for this product. Does not delete templates or saved designs.",
    )
    fastest_delivery_enabled = forms.BooleanField(
        required=False,
        label="Show fastest delivery",
        help_text="Show the fastest-delivery banner on this product page.",
    )
    fastest_delivery_min_business_days = forms.IntegerField(
        required=False,
        min_value=0,
        label="Earliest delivery (business days)",
        help_text="Business days from today. Saturday and Sunday are skipped.",
    )
    fastest_delivery_max_business_days = forms.IntegerField(
        required=False,
        min_value=0,
        label="Latest delivery (business days)",
        help_text="Must be equal to or greater than the earliest delivery.",
    )

    single_side_page_count = forms.IntegerField(
        required=False, min_value=1, max_value=20, label="Single Side — editable pages",
        help_text="Number of editor pages for Single Side. Leave blank to use existing behaviour.",
    )
    double_side_page_count = forms.IntegerField(
        required=False, min_value=1, max_value=20, label="Double Side — editable pages",
        help_text="Number of editor pages for Double Side. Leave blank to use existing behaviour.",
    )

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["minimum_quantity"].help_text = (
            "Minimum units per order. The storefront also enforces the first active "
            "quantity tier for the selected size, or the product-wide tier when no "
            "size-specific tiers exist. The higher minimum applies."
        )
        attrs = self.instance.source_attributes if (
            self.instance and isinstance(getattr(self.instance, "source_attributes", None), dict)
        ) else {}
        page_counts = attrs.get("printing_side_page_counts") or {}
        self.fields["single_side_page_count"].initial = page_counts.get("single")
        self.fields["double_side_page_count"].initial = page_counts.get("double")
        self.fields["show_customize_button"].initial = attrs.get("show_customize_button", True) is not False
        self.fields["fastest_delivery_enabled"].initial = bool(
            attrs.get("fastest_delivery_enabled", False)
        )
        self.fields["fastest_delivery_min_business_days"].initial = attrs.get(
            "fastest_delivery_min_business_days"
        )
        self.fields["fastest_delivery_max_business_days"].initial = attrs.get(
            "fastest_delivery_max_business_days"
        )

    def clean(self):
        cleaned = super().clean()
        enabled = cleaned.get("fastest_delivery_enabled")
        minimum = cleaned.get("fastest_delivery_min_business_days")
        maximum = cleaned.get("fastest_delivery_max_business_days")

        if enabled and (minimum is None or maximum is None):
            raise forms.ValidationError(
                "Enter both earliest and latest business days when fastest delivery is enabled."
            )
        if minimum is not None and maximum is not None and maximum < minimum:
            self.add_error(
                "fastest_delivery_max_business_days",
                "Latest delivery must be equal to or greater than earliest delivery.",
            )
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        attrs = dict(obj.source_attributes or {})
        counts = dict(attrs.get("printing_side_page_counts") or {})
        for key, field in (("single", "single_side_page_count"), ("double", "double_side_page_count")):
            count = self.cleaned_data.get(field)
            if count is None:
                counts.pop(key, None)
            else:
                counts[key] = int(count)
        if counts:
            attrs["printing_side_page_counts"] = counts
        else:
            attrs.pop("printing_side_page_counts", None)
        attrs["show_customize_button"] = bool(self.cleaned_data.get("show_customize_button", True))
        attrs["fastest_delivery_enabled"] = bool(
            self.cleaned_data.get("fastest_delivery_enabled", False)
        )

        minimum = self.cleaned_data.get("fastest_delivery_min_business_days")
        maximum = self.cleaned_data.get("fastest_delivery_max_business_days")

        if minimum is None:
            attrs.pop("fastest_delivery_min_business_days", None)
        else:
            attrs["fastest_delivery_min_business_days"] = int(minimum)

        if maximum is None:
            attrs.pop("fastest_delivery_max_business_days", None)
        else:
            attrs["fastest_delivery_max_business_days"] = int(maximum)

        obj.source_attributes = attrs
        if self.cleaned_data.get("clear_ms_client_secret"):
            obj.encrypted_ms_client_secret = ""
        elif self.cleaned_data.get("ms_client_secret"):
            obj.encrypted_ms_client_secret = encrypt_password(self.cleaned_data["ms_client_secret"])
        if commit:
            obj.save()
            self.save_m2m()
        return obj


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    inlines = [ProductImageInline, ProductSizeVariantInline, ProductPrintSurfaceInline, ProductPrintAreaInline, ProductColorVariantInline, ProductPriceTierInline]

    list_display = (
        "name", "category", "price", "min_price", "max_price",
        "minimum_quantity", "maximum_quantity",
        "is_active", "is_out_of_stock", "print_area_link",
    )
    list_filter = (
        ProductCategoryGroupFilter, ProductSubcategoryFilter,
        "is_on_sale", "is_active", "is_out_of_stock",
    )
    search_fields = ("name", "category__name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("price", "minimum_quantity", "is_active", "is_out_of_stock")
    list_per_page = 50
    list_select_related = ("category", "category__parent")

    fieldsets = (
        ("Storefront product details", {
            "fields": (
                "category", "name", "slug",
                "short_description",
                ("price", "min_price", "max_price"),
                ("minimum_quantity", "maximum_quantity"),
                "image", "hover_image",
                "editor_reference_image",
                "customizer_mode", "show_customize_button",
            ),
            "description": "Price range, minimum/maximum quantity and customer-facing product summary."
        }),
        ("Product content / tabs", {
            "fields": (
                "description", "product_information",
                "printing_method", "design_guidelines",
                "printing_guidelines", "faqs",
            ),
            "description": "Leave a section blank and it will be hidden on the product page."
        }),
        ("Universal editor configuration (opt-in)", {
            "fields": (
                "editor_layout_mode",
                ("workspace_width_in", "workspace_height_in"),
                ("constrain_to_print_area", "show_product_reference"),
                ("single_side_page_count", "double_side_page_count"),
            ),
            "description": "Leave Existing / legacy behaviour selected to preserve current templates exactly. Workspace dimensions control OUTER inch rulers only; printable dimensions remain separate.",
        }),
        ("Physical print size", {
            "fields": (
                "orientation",
                ("print_width_in", "print_height_in"),
                ("bleed_in", "safe_margin_in"),
                "min_dpi",
            ),
            "description": "Printable artwork dimensions in inches. These do not control the outer ruler for products using the new Admin-driven mode.",
        }),
        ("Default editable print area", {
            "fields": (
                "print_left_pct", "print_top_pct",
                "print_width_pct", "print_height_pct",
            ),
            "description": "Default editable area for the main product image."
        }),
        ("Sale", {
            "fields": ("is_on_sale", "sale_price", "sale_badge", "sale_priority"),
        }),
        ("Source", {
            "fields": ("source_attributes",),
            "classes": ("collapse",),
        }),
        ("Fastest delivery", {
            "fields": (
                "fastest_delivery_enabled",
                ("fastest_delivery_min_business_days", "fastest_delivery_max_business_days"),
            ),
            "description": (
                "Configure this product independently. Dates are calculated from the current "
                "date using Monday-Friday business days. Leave disabled to hide the banner."
            ),
        }),
        ("Availability", {
            "fields": ("is_active", "is_out_of_stock"),
        }),
    )

    class Media:
        css = {
            "all": ("designer/admin/zenvibe-richtext.css",)
        }
        js = ("designer/admin/zenvibe-richtext.js", "designer/admin/hide-legacy-3d-fields.js")

    def save_model(self, request, obj, form, change):
        # Capture the OLD Admin geometry before Product / inline surfaces are saved.
        # save_related() will compare this snapshot with the final Admin values.
        obj._zv_geometry_before_admin_save = (
            snapshot_product_geometry(obj.pk) if change and obj.pk else None
        )
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        # First save ProductPrintSurface / ProductSizeVariant inline edits normally.
        super().save_related(request, form, formsets, change)

        product = form.instance
        before = getattr(product, "_zv_geometry_before_admin_save", None)
        result = migrate_product_templates(
            product_id=product.pk,
            before_snapshot=before,
            reason="django-admin",
            changed_by=getattr(request.user, "get_username", lambda: "")(),
        )

        if result["geometry_changed"]:
            level = "warning" if result["errors"] else "success"
            self.message_user(
                request,
                (
                    f'Print geometry changed. Migrated {result["templates_migrated"]} '
                    f'of {result["templates_checked"]} master template(s); '
                    f'{result["templates_unchanged"]} already matched; '
                    f'{len(result["errors"])} error(s). '
                    f'Backup: {result.get("backup_file") or "not required"}.'
                ),
                level=level,
            )

    def print_area_link(self, obj):
        if not obj.id:
            return "Save first"
        if not obj.image and not obj.angle_images.exists():
            return "Upload a photo first"
        return format_html(
            '<a class="button" href="{}">Design print area</a>',
            reverse("designer:print_area_designer", args=[obj.id])
        )
    print_area_link.short_description = "Print Area"


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "banner_preview", "button_text", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "subtitle", "button_text")
    readonly_fields = ("banner_preview", "mobile_banner_preview")
    fieldsets = (
        ("Banner content", {"fields": ("title", "subtitle")}),
        ("Banner images", {"fields": ("image", "banner_preview", "mobile_image", "mobile_banner_preview"),
                           "description": "Upload the desktop banner and, optionally, a separate mobile banner."}),
        ("Call to action", {"fields": (("button_text", "button_url"),)}),
        ("Display", {"fields": ("sort_order", "is_active")}),
    )

    @admin.display(description="Desktop preview")
    def banner_preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="max-width:520px;max-height:180px;object-fit:cover;border-radius:8px" />', obj.image.url)
        return "No desktop banner uploaded"

    @admin.display(description="Mobile preview")
    def mobile_banner_preview(self, obj):
        if obj and obj.mobile_image:
            return format_html('<img src="{}" style="max-width:220px;max-height:260px;object-fit:cover;border-radius:8px" />', obj.mobile_image.url)
        return "Uses desktop banner"


@admin.register(PageContentBlock)
class PageContentBlockAdmin(admin.ModelAdmin):
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        page = request.GET.get("page")
        if page in dict(PageContentBlock.PAGE_CHOICES):
            initial["page"] = page
            defaults = {
                "our_work": ("hero", "Our Work"),
                "contact": ("intro", "Contact Us"),
            }
            if page in defaults:
                initial.setdefault("section_key", defaults[page][0])
                initial.setdefault("heading", defaults[page][1])
        return initial

    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse
        from django.utils.html import format_html
        from django.utils.safestring import mark_safe
        from urllib.parse import urlencode
        page = request.GET.get("page__exact")
        if page in ("our_work", "contact"):
            extra_context = dict(extra_context or {})
            add_url = reverse("admin:designer_pagecontentblock_add") + "?" + urlencode({"page": page})
            label = "Our Work" if page == "our_work" else "Contact Us"
            extra_context["title"] = f"{label} — Website Content"
            extra_context["subtitle"] = f"Manage {label} content blocks. If the list is empty, use Add Page content block to create the first section."
        return super().changelist_view(request, extra_context=extra_context)

    list_display = ("heading", "page", "section_key", "image_preview", "sort_order", "is_active")
    list_filter = ("page", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("heading", "subheading", "body", "section_key")
    ordering = ("page", "sort_order", "id")
    readonly_fields = ("image_preview_large",)
    fieldsets = (
        ("Page and position", {
            "fields": ("page", "section_key", "sort_order", "is_active"),
            "description": (
                "About page keys: hero, why-heading, why-01 to why-99, "
                "who-we-are, offer-heading, offer-01 to offer-99, contact. "
                "Cards are displayed by sort order. Disable a block to hide it."
            ),
        }),
        ("Section content", {
            "fields": ("subheading", "heading", "body", "image", "image_preview_large"),
            "description": "Body supports HTML. Images are uploaded locally and served from MEDIA.",
        }),
        ("Optional link / button", {
            "fields": ("button_text", "button_url"),
            "description": "For What We Offer cards, button_url can link the image/card to the matching category.",
        }),
    )

    @admin.display(description="Image")
    def image_preview(self, obj):
        if obj and obj.image:
            return format_html(
                '<img src="{}" style="width:70px;height:48px;object-fit:cover;border-radius:5px;border:1px solid #ddd" />',
                obj.image.url,
            )
        return "—"

    @admin.display(description="Current image")
    def image_preview_large(self, obj):
        if obj and obj.image:
            return format_html(
                '<img src="{}" style="max-width:520px;max-height:260px;object-fit:contain;background:#f6f6f6;padding:8px;border:1px solid #ddd;border-radius:8px" />',
                obj.image.url,
            )
        return "No image uploaded"



@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "company", "rating", "sort_order", "is_active")
    list_filter = ("is_active", "rating")
    search_fields = ("customer_name", "company", "review")
    list_editable = ("sort_order", "is_active")
    ordering = ("sort_order", "-id")


@admin.register(BrandLogo)
class BrandLogoAdmin(admin.ModelAdmin):
    list_display = ("name", "logo_preview", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    list_editable = ("sort_order", "is_active")
    readonly_fields = ("logo_preview",)
    fields = ("name", "image", "logo_preview", "website_url", "sort_order", "is_active")

    @admin.display(description="Preview")
    def logo_preview(self, obj):
        if obj and obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="max-width:180px;max-height:80px;object-fit:contain;'
                'border:1px solid #ddd;background:#fff;padding:6px;border-radius:6px" />',
                obj.image.url,
            )
        return "—"


# ============================================================
# GLOBAL SITE SETTINGS ADMIN
# ============================================================

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Single-record global website settings.

    Used by the storefront for:
    - Site name
    - Email
    - Phone
    - Address
    """

    list_display = (
        "site_name",
        "email",
        "phone",
        "address",
        "updated_at",
    )

    readonly_fields = (
        "updated_at",
    )

    fieldsets = (
        (
            "Website Information",
            {
                "fields": (
                    "site_name",
                ),
            },
        ),
        (
            "Contact Information",
            {
                "fields": (
                    "email",
                    "phone",
                    "address",
                ),
                "description": (
                    "These values are used by the About Us / Contact sections. "
                    "Email opens the mail application, phone uses the dialler, "
                    "and address opens Google Maps."
                ),
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        # ZenVibe only needs one global SiteSettings row.
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Prevent the global settings row from being accidentally removed.
        return False


class DesignTemplateCategoryForm(forms.ModelForm):
    category_filter = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True).order_by("parent__name", "name"),
        required=False,
        label="Product category",
        help_text="Select a category first to narrow the product list.",
    )

    class Meta:
        model = DesignTemplate
        fields = "__all__"

    class Media:
        js = ("designer/js/admin-template-product-filter.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = self.instance.product if self.instance and self.instance.pk else None
        if current:
            self.fields["category_filter"].initial = current.category_id
        categories = Category.objects.filter(is_active=True).order_by("parent__name", "name")
        self.fields["category_filter"].choices = [("", "Select category")] + [
            (str(c.pk), str(c)) for c in categories
        ]
        self.fields["product"].queryset = Product.objects.select_related("category").order_by("category__name", "name")
        self.fields["product"].widget.attrs["data-category-map"] = json.dumps({
            str(p.pk): str(p.category_id) for p in self.fields["product"].queryset
        })

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category_filter")
        product = cleaned.get("product")
        if category and product and product.category_id != category.pk:
            self.add_error("product", "Choose a product from the selected category.")
        return cleaned


@admin.register(DesignTemplate)
class DesignTemplateAdmin(admin.ModelAdmin):
    form = DesignTemplateCategoryForm
    list_display = ("id", "template_code", "name", "template_style", "product", "is_active", "updated_at", "preview_thumb", "open_builder")
    search_fields = ("name", "product__name")
    list_filter = ("is_active", "product__category")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at")
    fields = ("category_filter", "product", "name", "preview", "json_data", "is_active", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        # Allow Admin > Design Templates > Add to create a valid editable
        # multipage master. Do not replace JSON supplied by an administrator
        # and never rewrite existing published templates.
        if not change and not (obj.json_data or {}).get("pages") and not (obj.json_data or {}).get("objects"):
            surfaces = list(obj.product.print_surfaces.filter(is_active=True).order_by("sort_order", "id"))
            count = max(1, len(surfaces))
            pages = [{
                "name": surfaces[i].label if i < len(surfaces) else "Page {}".format(i + 1),
                "background": "#ffffff", "objects": []
            } for i in range(count)]
            obj.json_data = {"pages": pages}
        super().save_model(request, obj, form, change)

    def template_code(self, obj):
        return (obj.json_data or {}).get("business_card_code", "—")
    template_code.short_description = "Code"

    def template_style(self, obj):
        return (obj.json_data or {}).get("business_card_category", "—")
    template_style.short_description = "Style"

    def preview_thumb(self, obj):
        if obj.preview:
            cache_bust = int(obj.updated_at.timestamp()) if obj.updated_at else 0
            return format_html('<img src="{}?v={}" style="height:40px;border-radius:4px" />', obj.preview.url, cache_bust)
        return "—"
    preview_thumb.short_description = "Preview"

    def open_builder(self, obj):
        if obj.id:
            return format_html('<a class="button" href="{}" target="_blank">Open Builder</a>', reverse("designer:admin_template_builder", args=[obj.id]))
        return "Save first"
    open_builder.short_description = "Template Builder"


@admin.register(SavedDesign)
class SavedDesignAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "product",
        "quantity",
        "created_at"
    )



class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("from_status", "to_status", "note", "automatic", "changed_by", "created_at")
    fields = readonly_fields
    ordering = ("-created_at",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "design" and field is not None:
            # Choice labels need the name, not every saved artwork/preview payload.
            field.queryset = field.queryset.only("id", "name")
        return field

    list_display = ("order_number", "customer_name", "product_name", "quantity", "total", "payment_badge", "status", "created_at")
    list_filter = ("status", "payment_status", "payment_provider", "created_at", "design__product__category")
    search_fields = ("order_number", "customer_name", "customer_email", "customer_phone", "company", "design__product__name")
    list_editable = ("status",)
    readonly_fields = ("order_number", "created_at", "updated_at", "status_changed_at", "paid_at", "design_preview", "artwork_downloads")
    date_hierarchy = "created_at"
    inlines = [OrderStatusHistoryInline]
    fieldsets = (
        ("Order & artwork", {"fields": ("order_number", "status", "payment_status", "payment_provider", "design", "design_preview", "artwork_downloads", "quantity", "unit_price", "total")}),
        ("Customer", {"fields": ("user", "customer_name", "customer_email", "customer_phone", "company")}),
        ("Delivery", {"fields": ("address", "city", "province", "postal_code")}),
        ("Payment / Stripe", {"fields": ("stripe_checkout_session_id", "paid_at")}),
        ("Notes & timing", {"fields": ("customer_notes", "admin_notes", "created_at", "updated_at", "status_changed_at")}),
    )
    def product_name(self, obj): return obj.design.product.name if obj.design and obj.design.product else "—"
    product_name.short_description = "Product"
    def payment_badge(self, obj):
        colors={"paid":"#198754","bypassed":"#6f42c1","pending":"#d98200","failed":"#c62828","refunded":"#52606d"}
        return format_html('<span style="padding:4px 8px;border-radius:20px;background:{}18;color:{};font-weight:800">{}</span>', colors.get(obj.payment_status,"#52606d"), colors.get(obj.payment_status,"#52606d"), obj.get_payment_status_display())
    payment_badge.short_description = "Payment"
    def design_preview(self, obj):
        if obj.design and obj.design.preview_png:
            return format_html('<div class="zv-order-artwork"><img src="{}" style="max-width:420px;max-height:320px;border-radius:12px;border:1px solid #ddd;background:#fff" /></div>', obj.design.preview_png)
        return "No preview"
    def artwork_downloads(self, obj):
        if not obj.pk or not obj.design or not obj.design.preview_png: return "Save/order artwork first"
        links=[]
        for fmt,label in (("png","PNG"),("jpg","JPG"),("jpeg","JPEG"),("pdf","PDF")):
            url=reverse("designer:admin_order_artwork_download", args=[obj.pk, fmt])
            links.append(f'<a class="button" style="margin:3px" href="{url}">Download {label}</a>')
        return format_html(''.join(links))
    artwork_downloads.short_description = "Customer customised artwork"
    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = Order.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if old_status and old_status != obj.status:
            OrderStatusHistory.objects.create(order=obj, from_status=old_status, to_status=obj.status, note="Updated by administrator", changed_by=request.user, automatic=False)
            from .services.order_workflow import send_status_email
            send_status_email(obj, old_status)

@admin.register(OrderWorkflowConfig)
class OrderWorkflowConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Payments", {"fields": ("name", "is_active", "payment_mode", "currency")}),
        ("Notifications", {"fields": ("admin_notification_emails", "email_admin_on_order", "email_customer_on_order", "email_customer_on_status_change")}),
        ("Automatic order lifecycle", {"fields": ("auto_confirm", "confirm_after_minutes", "auto_start_production", "production_after_hours", "auto_ship", "ship_after_days", "auto_complete", "complete_after_days"), "description":"Run `python manage.py sync_order_statuses` from cPanel Cron (for example every 5 minutes) so configured stages advance automatically."}),
    )
    list_display = ("name", "payment_mode", "auto_confirm", "auto_start_production", "auto_ship", "auto_complete", "is_active")
    def has_add_permission(self, request):
        return not OrderWorkflowConfig.objects.exists()
    def get_model_perms(self, request):
        # Keep the legacy workflow URL available but hide its duplicate admin entry.
        return {}


from .models import PaymentSetup


@admin.register(PaymentSetup)
class PaymentSetupAdmin(OrderWorkflowConfigAdmin):
    """Dedicated payment menu; edits the same existing configuration record."""
    def get_model_perms(self, request):
        return admin.ModelAdmin.get_model_perms(self, request)

    def has_add_permission(self, request):
        return not OrderWorkflowConfig.objects.exists()


# Dashboard metrics supplied to templates/admin/index.html.
from django.db.models import Sum
from django.contrib.admin.sites import AdminSite

def _zenvibe_admin_index(request, extra_context=None):
    from .models import Order, Product, OrderWorkflowConfig
    from .services.order_workflow import sync_all_orders
    sync_all_orders()
    extra_context = dict(extra_context or {})
    active_orders = Order.objects.exclude(status="cancelled")
    extra_context.update({
        "zv_total_orders": Order.objects.count(),
        "zv_new_orders": Order.objects.filter(status="new").count(),
        "zv_revenue": active_orders.aggregate(v=Sum("total"))["v"] or 0,
        "zv_products": Product.objects.filter(is_active=True).count(),
        "zv_pending_payments": Order.objects.filter(payment_status="pending").count(),
        "zv_workflow": OrderWorkflowConfig.current(),
        "zv_recent_orders": Order.objects.select_related("design__product").all()[:8],
        "zv_chart_rows": [
            {
                "month": o.created_at.strftime("%Y-%m"),
                "status": o.status,
                "status_label": o.get_status_display(),
                "payment": o.payment_status,
                "payment_label": o.get_payment_status_display(),
                "category": o.design.product.category.name if o.design_id and o.design.product_id and o.design.product.category_id else "Uncategorised",
                "quantity": o.quantity,
                "total": float(o.total or 0),
            }
            for o in Order.objects.select_related("design__product__category").all()
        ],
        "zv_best_sellers": Product.objects.filter(is_active=True).select_related("category").annotate(units_sold=Sum("saveddesign__orders__quantity")).order_by("-units_sold", "name")[:6],
    })
    return AdminSite.index(admin.site, request, extra_context=extra_context)

admin.site.index = _zenvibe_admin_index


@admin.register(ChatbotKnowledge)
class ChatbotKnowledgeAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "is_active", "sort_order", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("question", "answer", "keywords")
    list_editable = ("is_active", "sort_order")
    fieldsets = (("Training question", {"fields": ("category", "question", "answer", "keywords")}), ("Visibility", {"fields": ("is_active", "sort_order")}))

@admin.register(ChatInquiry)
class ChatInquiryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "phone", "status", "short_message")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "phone", "message")
    list_editable = ("status",)
    readonly_fields = ("created_at", "session_key", "page_url")
    def short_message(self, obj):
        return (obj.message[:80] + "…") if len(obj.message) > 80 else obj.message
    short_message.short_description = "Inquiry"

# ============================================================
# BLOG ADMIN
# ============================================================


class BlogPostImageInline(admin.TabularInline):
    """
    Allows additional article images to be uploaded directly
    while editing a blog post.
    """

    model = BlogPostImage
    extra = 1

    fields = (
        "image_preview",
        "image",
        "alt_text",
        "caption",
        "sort_order",
    )

    readonly_fields = (
        "image_preview",
    )

    ordering = (
        "sort_order",
        "id",
    )

    def image_preview(self, obj):

        if obj and obj.pk and obj.image:

            return format_html(
                '<img src="{}" '
                'style="width:130px;'
                'height:80px;'
                'object-fit:cover;'
                'border:1px solid #e1e6ed;'
                'border-radius:8px;'
                'background:#fff;" />',
                obj.image.url,
            )

        return "—"

    image_preview.short_description = "Preview"


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):

    inlines = [
        BlogPostImageInline,
    ]

    list_display = (
        "featured_thumbnail",
        "title",
        "category",
        "author_name",
        "published_at",
        "comment_count",
        "is_published",
        "allow_comments",
    )

    list_display_links = (
        "featured_thumbnail",
        "title",
    )

    list_filter = (
        "is_published",
        "allow_comments",
        "category",
        "published_at",
    )

    search_fields = (
        "title",
        "slug",
        "category",
        "author_name",
        "excerpt",
        "body",
    )

    prepopulated_fields = {
        "slug": (
            "title",
        )
    }

    list_editable = (
        "is_published",
        "allow_comments",
    )

    readonly_fields = (
        "featured_image_preview",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-published_at",
        "-id",
    )

    date_hierarchy = "published_at"

    fieldsets = (

        (
            "Blog Article",
            {
                "fields": (
                    "title",
                    "slug",
                    "category",
                    "author_name",
                )
            },
        ),

        (
            "Article Introduction",
            {
                "fields": (
                    "excerpt",
                ),
                "description": (
                    "This short description is displayed on the "
                    "main blog page below the article title."
                ),
            },
        ),

        (
            "Article Content",
            {
                "fields": (
                    "body",
                ),
                "description": (
                    "Enter the complete article content here. "
                    "Paragraphs and line breaks will be preserved "
                    "on the website."
                ),
            },
        ),

        (
            "Featured Image",
            {
                "fields": (
                    "featured_image_preview",
                    "image",
                    "image_alt",
                ),
                "description": (
                    "This is the main blog image. It appears on "
                    "the blog listing and at the top of the article."
                ),
            },
        ),

        (
            "Publishing",
            {
                "fields": (
                    "is_published",
                    "published_at",
                    "allow_comments",
                ),
            },
        ),

        (
            "SEO",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "seo_title",
                    "seo_description",
                ),
            },
        ),

        (
            "System Information",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def featured_thumbnail(self, obj):

        if obj.image:

            return format_html(
                '<img src="{}" '
                'style="width:80px;'
                'height:52px;'
                'object-fit:cover;'
                'border-radius:6px;'
                'border:1px solid #e2e6eb;" />',
                obj.image.url,
            )

        return format_html(
            '<div style="'
            'width:80px;'
            'height:52px;'
            'border-radius:6px;'
            'background:#0b3f79;'
            'color:#fff;'
            'display:flex;'
            'align-items:center;'
            'justify-content:center;'
            'font-weight:800;'
            'font-size:20px;'
            '">Z</div>'
        )

    featured_thumbnail.short_description = "Image"

    def featured_image_preview(self, obj):

        if obj and obj.pk and obj.image:

            return format_html(
                '<div style="margin-bottom:10px;">'
                '<img src="{}" '
                'style="'
                'width:100%;'
                'max-width:650px;'
                'max-height:360px;'
                'object-fit:contain;'
                'border:1px solid #e1e5ea;'
                'border-radius:10px;'
                'background:#f8f9fb;'
                'padding:5px;'
                '" />'
                '</div>',
                obj.image.url,
            )

        return "Upload a featured image below."

    featured_image_preview.short_description = "Current Featured Image"

    def comment_count(self, obj):

        approved = obj.comments.filter(
            is_approved=True
        ).count()

        pending = obj.comments.filter(
            is_approved=False
        ).count()

        if pending:

            return format_html(
                '<span title="{} approved, {} awaiting approval">'
                '<strong>{}</strong> '
                '<span style="color:#d97706;">(+{} pending)</span>'
                '</span>',
                approved,
                pending,
                approved,
                pending,
            )

        return format_html(
            '<span>{}</span>',
            approved,
        )

    comment_count.short_description = "Comments"


# ============================================================
# BLOG COMMENTS
# ============================================================


@admin.action(
    description="Approve selected comments"
)
def approve_blog_comments(
    modeladmin,
    request,
    queryset
):

    updated = queryset.update(
        is_approved=True
    )

    modeladmin.message_user(
        request,
        f"{updated} comment(s) approved."
    )


@admin.action(
    description="Move selected comments back to pending"
)
def unapprove_blog_comments(
    modeladmin,
    request,
    queryset
):

    updated = queryset.update(
        is_approved=False
    )

    modeladmin.message_user(
        request,
        f"{updated} comment(s) moved to pending."
    )


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "article_title",
        "email",
        "comment_preview",
        "created_at",
        "approval_status",
        "is_approved",
    )

    list_display_links = (
        "name",
        "article_title",
    )

    list_filter = (
        "is_approved",
        "created_at",
        "post",
    )

    search_fields = (
        "name",
        "email",
        "website",
        "comment",
        "post__title",
    )

    list_editable = (
        "is_approved",
    )

    readonly_fields = (
        "post",
        "name",
        "email",
        "website",
        "comment",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    actions = (
        approve_blog_comments,
        unapprove_blog_comments,
    )

    fieldsets = (

        (
            "Comment",
            {
                "fields": (
                    "post",
                    "comment",
                    "is_approved",
                )
            },
        ),

        (
            "Customer",
            {
                "fields": (
                    "name",
                    "email",
                    "website",
                )
            },
        ),

        (
            "Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),

    )

    def article_title(self, obj):

        return obj.post.title

    article_title.short_description = "Blog Article"

    def comment_preview(self, obj):

        text = obj.comment or ""

        if len(text) > 90:
            return text[:90] + "…"

        return text

    comment_preview.short_description = "Comment"

    def approval_status(self, obj):

        if obj.is_approved:

            return format_html(
                '<span style="'
                'display:inline-block;'
                'padding:4px 9px;'
                'border-radius:20px;'
                'background:#e7f6ec;'
                'color:#198754;'
                'font-weight:700;'
                '">Approved</span>'
            )

        return format_html(
            '<span style="'
            'display:inline-block;'
            'padding:4px 9px;'
            'border-radius:20px;'
            'background:#fff3cd;'
            'color:#8a6500;'
            'font-weight:700;'
            '">Pending</span>'
        )

    approval_status.short_description = "Status"


# Store management admins are registered below in this module.
# Do not import admin_email here: it also registers these models.


# Store-management entries used by the custom admin sidebar.
from .models import DiscountCoupon, StoreEmailAccount, StoreEmailTemplate

class DiscountCouponAdminForm(forms.ModelForm):
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "zv-coupon-products"}),
        help_text="Select one or more products. This code applies only to the checked products. Search does not clear your selections.",
    )

    class Meta:
        model = DiscountCoupon
        fields = "__all__"


@admin.register(DiscountCoupon)
class DiscountCouponAdmin(admin.ModelAdmin):
    form = DiscountCouponAdminForm
    fields = ("code", "title", "products", "discount_type", "value", "starts_at", "expires_at", "is_active", "show_at_checkout")
    change_form_template = "admin/designer/discountcoupon/change_form.html"

    list_display = ("code", "title", "discount_type", "value", "is_active", "show_at_checkout")
    search_fields = ("code", "title")
    list_filter = ("discount_type", "is_active", "show_at_checkout")

class StoreEmailAccountForm(forms.ModelForm):
    gmail_app_password = forms.CharField(required=False, label="Gmail App Password", widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}), help_text="Use a Google App Password, not your login password. Leave blank to keep the saved secret.")
    clear_gmail_password = forms.BooleanField(required=False, label="Remove saved Gmail App Password")
    ms_client_secret = forms.CharField(required=False, label="Microsoft Graph Client Secret", widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}), help_text="Azure app registration client secret VALUE. Leave blank to retain existing secret.")
    clear_ms_client_secret = forms.BooleanField(required=False, label="Remove saved Microsoft Client Secret")

    class Meta:
        model = StoreEmailAccount
        fields = ("provider", "email_address", "ms_tenant_id", "ms_client_id", "is_active", "notify_on_order", "notify_on_contact")

    def clean(self):
        data = super().clean()
        if data.get("clear_gmail_password") and data.get("gmail_app_password"):
            raise forms.ValidationError("Choose either replace or remove the Gmail password.")
        if data.get("gmail_app_password") and data.get("provider") != "gmail":
            raise forms.ValidationError("Only Gmail mailboxes accept a Gmail App Password.")
        if data.get("clear_ms_client_secret") and data.get("ms_client_secret"):
            raise forms.ValidationError("Choose either replace or remove the Microsoft client secret.")
        if data.get("ms_client_secret") and data.get("provider") != "outlook":
            raise forms.ValidationError("Microsoft client secret can only be set for Outlook.")
        return data

    def save(self, commit=True):
        from designer.services.mail_credentials import encrypt_password
        obj = super().save(commit=False)
        if self.cleaned_data.get("clear_gmail_password"):
            obj.encrypted_app_password = ""
        elif self.cleaned_data.get("gmail_app_password"):
            obj.encrypted_app_password = encrypt_password(self.cleaned_data["gmail_app_password"].replace(" ", ""))
        if commit:
            obj.save()
            self.save_m2m()
        return obj


@admin.register(StoreEmailAccount)
class StoreEmailAccountAdmin(admin.ModelAdmin):
    form = StoreEmailAccountForm
    fieldsets = (("Mailbox", {"fields": ("provider", "email_address", "gmail_app_password", "clear_gmail_password", "ms_tenant_id", "ms_client_id", "ms_client_secret", "clear_ms_client_secret", "connection_status", "is_active")}), ("Notifications", {"fields": ("notify_on_order", "notify_on_contact")}),)
    """Show configuration readiness and offer a real SMTP/Graph test in admin."""
    list_display = ("email_address", "provider", "connection_status", "is_active", "notify_on_order", "notify_on_contact")
    readonly_fields = ("connection_status",)
    search_fields = ("email_address",)
    list_filter = ("provider", "is_active")
    actions = ("send_connection_test",)

    @admin.display(description="Connection configuration")
    def connection_status(self, obj):
        import os
        if not obj or not obj.pk:
            return "Save the mailbox, then check connection readiness."
        if obj.provider == "gmail":
            configured = bool(obj.encrypted_app_password or os.environ.get("ZV_GMAIL_APP_PASSWORD"))
            detail = "Gmail app password is configured" if configured else "Missing ZV_GMAIL_APP_PASSWORD on server"
        elif obj.provider == "outlook":
            keys = ("ZV_MS_TENANT_ID", "ZV_MS_CLIENT_ID", "ZV_MS_CLIENT_SECRET")
            missing = [key for key, present in zip(keys, (obj.ms_tenant_id or os.environ.get(keys[0]), obj.ms_client_id or os.environ.get(keys[1]), obj.encrypted_ms_client_secret or os.environ.get(keys[2]))) if not present]
            configured = not missing
            detail = "Microsoft Graph credentials configured" if configured else "Missing server settings: " + ", ".join(missing)
        else:
            configured = False
            detail = "Select Gmail or Outlook"
        if not obj.is_active:
            detail += " (mailbox inactive)"
        return detail + (" — run Send connection test to verify delivery" if configured else "")

    @admin.action(description="Send connection test to selected mailbox address")
    def send_connection_test(self, request, queryset):
        from django.contrib import messages
        from designer.services.store_email import test_store_email
        for account in queryset:
            if not account.is_active:
                self.message_user(request, f"{account.email_address}: activate mailbox before testing.", level=messages.WARNING)
                continue
            try:
                test_store_email(account, account.email_address)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).exception("Store mailbox test failed")
                self.message_user(request, f"{account.email_address}: test failed. Check server mail credentials and logs.", level=messages.ERROR)
            else:
                self.message_user(request, f"Test email sent to {account.email_address}. Check inbox/spam.", level=messages.SUCCESS)


@admin.register(StoreEmailTemplate)
class StoreEmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("event", "subject", "enabled")
    search_fields = ("event", "subject")
    list_filter = ("enabled",)
