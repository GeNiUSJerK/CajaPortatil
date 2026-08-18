from django.db import models

class Producto(models.Model):
    codigo_barras = models.CharField(max_length=255, unique=True, db_index=True)
    nombre = models.CharField(max_length=150)
    marca = models.CharField(max_length=100, blank=True, null=True)
    talla = models.CharField(max_length=20, blank=True, null=True)
    precio_costo = models.PositiveIntegerField()
    precio_venta = models.PositiveIntegerField()
    stock = models.IntegerField(default=1)
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo_barras})"

class Venta(models.Model):
    METODOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia / Débito'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField()
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='EFECTIVO')
    monto_recibido = models.PositiveIntegerField(default=0)
    vuelto = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Venta {self.id} - ${self.total}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    producto_nombre = models.CharField(max_length=150, blank=True, null=True)
    precio_costo_historico = models.PositiveIntegerField(blank=True, null=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.PositiveIntegerField()
    subtotal = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"
