from django.contrib import admin
from django.forms.widgets import Textarea
from .services.account_pool.models import ServiceAccount


class ServiceAccountAdmin(admin.ModelAdmin):
    list_display = ("phone_num", "client", "status", "usage")
    list_filter = ("client", "status")
    search_fields = ("phone_num", "client")
    readonly_fields = ("usage",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=None, **kwargs)
        if "credentials" in form.base_fields:
            form.base_fields["credentials"].widget = Textarea(
                attrs={"rows": 12, "style": "font-family: monospace; width: 90%;"}
            )
            form.base_fields["credentials"].help_text = (
                "Paste Python dict format (single quotes) or JSON format (double quotes). "
                "Example: {'accept': '*/*', 'content-type': 'application/json'} or "
                '{"accept": "*/*", "content-type": "application/json"}'
            )
        return form

    def save_model(self, request, obj, form, change):
        """Ensure usage is set to 0 if not provided."""
        if not change and obj.usage is None:
            obj.usage = 0
        super().save_model(request, obj, form, change)


admin.site.register(ServiceAccount, ServiceAccountAdmin)
