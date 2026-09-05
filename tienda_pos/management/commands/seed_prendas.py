import random
from django.core.management.base import BaseCommand
from tienda_pos.models import Categoria, Producto

class Command(BaseCommand):
    help = 'Crea prendas de prueba'

    def handle(self, *args, **kwargs):
        prendas = [
            ("Jeans", "Jeans Azul Claro", "Index", "38", 5000, 10000),
            ("Jeans", "Jeans Negro Roto", "Marquis", "40", 6000, 12000),
            ("Camisas", "Camisa Blanca Lisa", "Zara", "M", 4000, 8000),
            ("Camisas", "Camisa Cuadros", "H&M", "L", 4500, 9000),
            ("Tops", "Top Deportivo Negro", "Nike", "S", 3000, 6000),
            ("Faldas", "Falda Corta Negra", "Index", "M", 3500, 7000),
            ("Faldas", "Falda Midi Floral", "Marquis", "L", 4000, 8000),
            ("Short", "Short Denim", "Levis", "36", 5000, 10000),
            ("Segunda Mano", "Chaqueta Vintage", "Desconocida", "L", 2000, 15000)
        ]

        for cat_name, nombre, marca, talla, costo, venta in prendas:
            try:
                cat = Categoria.objects.get(nombre=cat_name)
                codigo = str(random.randint(100000000000, 999999999999))
                Producto.objects.get_or_create(
                    codigo_barras=codigo, 
                    defaults={
                        'nombre': nombre, 
                        'categoria': cat, 
                        'marca': marca, 
                        'talla': talla, 
                        'precio_costo': costo, 
                        'precio_venta': venta, 
                        'stock': random.randint(1, 10)
                    }
                )
                self.stdout.write(self.style.SUCCESS(f'Creado: {nombre}'))
            except Categoria.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Categoria {cat_name} no existe'))
