import json
import os
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.conf import settings
from .models import Producto, Venta, DetalleVenta

def index(request):
    return render(request, 'tienda_pos/index.html')

def api_buscar_producto(request, codigo):
    try:
        producto = Producto.objects.get(codigo_barras=codigo, activo=True)
        data = {
            'existe': True,
            'id': producto.id,
            'codigo_barras': producto.codigo_barras,
            'nombre': producto.nombre,
            'marca': producto.marca,
            'talla': producto.talla,
            'precio_costo': producto.precio_costo,
            'precio_venta': producto.precio_venta,
            'stock': producto.stock,
        }
    except Producto.DoesNotExist:
        data = {'existe': False}
    return JsonResponse(data)

@csrf_exempt
def api_guardar_producto(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            codigo = data.get('codigo_barras')
            
            producto, created = Producto.objects.get_or_create(
                codigo_barras=codigo,
                defaults={
                    'nombre': data.get('nombre', ''),
                    'marca': data.get('marca', ''),
                    'talla': data.get('talla', ''),
                    'precio_costo': data.get('precio_costo', 0),
                    'precio_venta': data.get('precio_venta', 0),
                    'stock': data.get('stock', 0)
                }
            )
            
            if not created:
                # Actualizar existente
                if 'nombre' in data: producto.nombre = data['nombre']
                if 'marca' in data: producto.marca = data['marca']
                if 'talla' in data: producto.talla = data['talla']
                if 'precio_costo' in data: producto.precio_costo = data['precio_costo']
                if 'precio_venta' in data: producto.precio_venta = data['precio_venta']
                if 'stock' in data: 
                    # Se suma al stock actual, o se puede reescribir dependiendo del flujo. 
                    # El prompt dice "Sumar Stock", así que lo sumamos.
                    # Asumiremos que el frontend envía la cantidad a AÑADIR o el nuevo total. 
                    # Vamos a sobrescribir si el usuario edita o sumar. 
                    # Haremos que el frontend mande el stock absoluto que debe quedar.
                    producto.stock = data['stock']
                producto.save()

            return JsonResponse({'success': True, 'producto_id': producto.id, 'mensaje': 'Prenda guardada exitosamente 🐾'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


@csrf_exempt
def api_procesar_venta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            carrito = data.get('carrito', [])
            metodo_pago = data.get('metodo_pago', 'EFECTIVO')
            monto_recibido = int(data.get('monto_recibido', 0))
            total_regateado = data.get('total_regateado')
            
            if not carrito:
                return JsonResponse({'success': False, 'error': 'El carrito está vacío'}, status=400)

            with transaction.atomic():
                total_venta = 0
                detalles_a_crear = []
                
                # Validar stock y calcular total
                for item in carrito:
                    producto = Producto.objects.select_for_update().get(id=item['id'])
                    cantidad = int(item['cantidad'])
                    
                    if producto.stock < cantidad:
                        raise ValueError(f"Stock insuficiente para {producto.nombre} (Disp: {producto.stock})")
                    
                    subtotal = cantidad * producto.precio_venta
                    total_venta += subtotal
                    
                    # Descontar stock
                    producto.stock -= cantidad
                    producto.save()
                    
                    detalles_a_crear.append({
                        'producto': producto,
                        'cantidad': cantidad,
                        'precio_unitario': producto.precio_venta,
                        'subtotal': subtotal
                    })

                # Si hay precio regateado, se sobreescribe el total calculado
                if total_regateado is not None and int(total_regateado) > 0:
                    total_venta = int(total_regateado)

                vuelto = 0
                if metodo_pago == 'EFECTIVO':
                    if monto_recibido < total_venta:
                        raise ValueError(f"Monto recibido insuficiente. Faltan ${total_venta - monto_recibido}")
                    vuelto = monto_recibido - total_venta
                else:
                    monto_recibido = total_venta # Para transferencia, asumimos que se recibe exacto

                venta = Venta.objects.create(
                    total=total_venta,
                    metodo_pago=metodo_pago,
                    monto_recibido=monto_recibido,
                    vuelto=vuelto
                )

                for detalle in detalles_a_crear:
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=detalle['producto'],
                        cantidad=detalle['cantidad'],
                        precio_unitario=detalle['precio_unitario'],
                        subtotal=detalle['subtotal']
                    )

            return JsonResponse({'success': True, 'venta_id': venta.id, 'vuelto': vuelto, 'mensaje': 'Venta concretada 🐱✨'})
        
        except Producto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Un producto en el carrito no existe'}, status=400)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


def api_listar_inventario(request):
    query = request.GET.get('q', '')
    productos = Producto.objects.filter(activo=True).order_by('-actualizado_en')
    
    if query:
        productos = productos.filter(nombre__icontains=query) | \
                    productos.filter(marca__icontains=query) | \
                    productos.filter(codigo_barras__icontains=query)
                    
    data = []
    for p in productos:
        data.append({
            'id': p.id,
            'codigo_barras': p.codigo_barras,
            'nombre': p.nombre,
            'marca': p.marca,
            'talla': p.talla,
            'precio_costo': p.precio_costo,
            'precio_venta': p.precio_venta,
            'stock': p.stock,
        })
    return JsonResponse({'productos': data})

@csrf_exempt
def api_eliminar_producto(request, id):
    if request.method == 'POST':
        try:
            producto = Producto.objects.get(id=id)
            producto.activo = False
            producto.save()
            return JsonResponse({'success': True, 'mensaje': 'Producto eliminado correctamente'})
        except Producto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

def api_historial_ventas(request):
    ventas = Venta.objects.all().order_by('-fecha')[:50] # Mostrar las últimas 50 ventas
    data = []
    for v in ventas:
        detalles = []
        ganancia_total = 0
        for d in v.detalles.all():
            costo_total = d.producto.precio_costo * d.cantidad if d.producto else 0
            ganancia = d.subtotal - costo_total
            ganancia_total += ganancia
            detalles.append({
                'producto_nombre': d.producto.nombre if d.producto else 'Producto Desconocido',
                'cantidad': d.cantidad,
                'precio_unitario': d.precio_unitario,
                'subtotal': d.subtotal,
                'ganancia': ganancia
            })
        data.append({
            'id': v.id,
            'fecha': v.fecha.strftime('%d/%m/%Y %H:%M'),
            'total': v.total,
            'ganancia_total': ganancia_total,
            'metodo_pago': v.get_metodo_pago_display(),
            'monto_recibido': v.monto_recibido,
            'vuelto': v.vuelto,
            'detalles': detalles
        })
    return JsonResponse({'ventas': data})


def descargar_bd(request):
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    if os.path.exists(db_path):
        return FileResponse(open(db_path, 'rb'), as_attachment=True, filename='db_backup.sqlite3')
    return JsonResponse({'error': 'Base de datos no encontrada'}, status=404)
