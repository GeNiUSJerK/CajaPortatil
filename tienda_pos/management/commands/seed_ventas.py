import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from tienda_pos.models import Producto, Venta, DetalleVenta

class Command(BaseCommand):
    help = 'Simula ventas de prueba'

    def handle(self, *args, **kwargs):
        productos = list(Producto.objects.all())
        if not productos:
            self.stdout.write(self.style.ERROR('No hay productos para vender.'))
            return

        metodos = ['EFECTIVO', 'TARJETA', 'TRANSFERENCIA']
        
        for i in range(5):
            # Create a sale
            metodo = random.choice(metodos)
            venta = Venta.objects.create(
                metodo_pago=metodo,
                total=0
            )
            
            # Add 2 to 4 items from different categories
            total_venta = 0
            ganancia_venta = 0
            
            # Agrupar productos por categoría
            cats = {}
            for p in productos:
                if p.categoria_id not in cats:
                    cats[p.categoria_id] = []
                cats[p.categoria_id].append(p)
            
            # Elegir 3 categorías distintas (o las que haya)
            chosen_cats = random.sample(list(cats.keys()), min(3, len(cats)))
            items_to_buy = [random.choice(cats[c]) for c in chosen_cats]

            for p in items_to_buy:
                cantidad = random.randint(1, 2)
                subtotal = cantidad * p.precio_venta
                ganancia = subtotal - (cantidad * p.precio_costo)
                
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=p,
                    producto_nombre=p.nombre,
                    cantidad=cantidad,
                    precio_costo_historico=p.precio_costo,
                    precio_unitario=p.precio_venta,
                    subtotal=subtotal
                )
                
                total_venta += subtotal
                ganancia_venta += ganancia
                
                # Reduce stock
                if p.stock >= cantidad:
                    p.stock -= cantidad
                    p.save()
            
            venta.total = total_venta
            venta.save()
            
            self.stdout.write(self.style.SUCCESS(f'Venta simulada creada por ${total_venta}'))
