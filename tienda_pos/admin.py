from django.contrib import admin
from .models import Producto, Venta, DetalleVenta

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo_barras', 'nombre', 'marca', 'talla', 'precio_venta', 'stock', 'actualizado_en')
    search_fields = ('codigo_barras', 'nombre', 'marca')
    list_filter = ('marca', 'talla')
    ordering = ('-actualizado_en',)

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal')

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'total', 'metodo_pago')
    list_filter = ('metodo_pago', 'fecha')
    inlines = [DetalleVentaInline]
    readonly_fields = ('fecha', 'total', 'metodo_pago', 'monto_recibido', 'vuelto')
