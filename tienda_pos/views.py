import json
import os
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.conf import settings
from django.utils.timezone import localtime
from .models import Producto, Venta, DetalleVenta, Categoria

def index(request):
    return render(request, 'tienda_pos/index.html')

def api_buscar_producto(request, codigo):
    try:
        producto = Producto.objects.get(codigo_barras=codigo)
        data = {
            'existe': True,
            'id': producto.id,
            'codigo_barras': producto.codigo_barras,
            'nombre': producto.nombre,
            'marca': producto.marca,
            'categoria_id': producto.categoria_id,
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
            is_json = request.content_type == 'application/json'
            if is_json:
                data = json.loads(request.body)
            else:
                data = request.POST

            codigo = data.get('codigo_barras')
            categoria_id = data.get('categoria_id')
            categoria = None
            if categoria_id:
                try:
                    categoria = Categoria.objects.get(id=categoria_id)
                except Categoria.DoesNotExist:
                    pass
            
            precio_costo = int(data.get('precio_costo', 0)) if data.get('precio_costo') else 0
            precio_venta = int(data.get('precio_venta', 0)) if data.get('precio_venta') else 0
            stock = int(data.get('stock', 0)) if data.get('stock') else 0

            producto, created = Producto.objects.get_or_create(
                codigo_barras=codigo,
                defaults={
                    'nombre': data.get('nombre', ''),
                    'categoria': categoria,
                    'marca': data.get('marca', ''),
                    'talla': data.get('talla', ''),
                    'precio_costo': precio_costo,
                    'precio_venta': precio_venta,
                    'stock': stock
                }
            )
            
            if not created:
                if 'nombre' in data: producto.nombre = data['nombre']
                if 'categoria_id' in data: producto.categoria = categoria
                if 'marca' in data: producto.marca = data.get('marca', '')
                if 'talla' in data: producto.talla = data.get('talla', '')
                if 'precio_costo' in data: producto.precio_costo = precio_costo
                if 'precio_venta' in data: producto.precio_venta = precio_venta
                if 'stock' in data: producto.stock = stock
                
            if not is_json and 'imagen' in request.FILES:
                producto.imagen = request.FILES['imagen']
                
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
                        'producto_nombre': producto.nombre,
                        'precio_costo_historico': producto.precio_costo,
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
                        producto_nombre=detalle['producto_nombre'],
                        precio_costo_historico=detalle['precio_costo_historico'],
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
    categoria_id = request.GET.get('categoria', '')
    productos = Producto.objects.all().order_by('-actualizado_en')
    
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

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
            'categoria_nombre': p.categoria.nombre if p.categoria else None,
            'precio_venta': p.precio_venta,
            'stock': p.stock,
            'imagen_url': p.imagen.url if p.imagen else None
        })
    
    return JsonResponse({'success': True, 'productos': data})

@csrf_exempt
def api_eliminar_producto(request, id):
    if request.method == 'POST':
        try:
            producto = Producto.objects.get(id=id)
            producto.delete()
            return JsonResponse({'success': True, 'mensaje': 'Producto eliminado completamente'})
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
            costo = d.precio_costo_historico if d.precio_costo_historico is not None else (d.producto.precio_costo if d.producto else 0)
            costo_total = costo * d.cantidad
            ganancia = d.subtotal - costo_total
            ganancia_total += ganancia
            
            nombre = d.producto_nombre if d.producto_nombre else (d.producto.nombre if d.producto else 'Producto Eliminado')
            categoria = 'Sin Categoría'
            if d.producto and d.producto.categoria:
                categoria = d.producto.categoria.nombre
            
            detalles.append({
                'producto_nombre': nombre,
                'categoria_nombre': categoria,
                'cantidad': d.cantidad,
                'precio_unitario': d.precio_unitario,
                'subtotal': d.subtotal,
                'ganancia': ganancia
            })
        data.append({
            'id': v.id,
            'fecha': localtime(v.fecha).strftime('%d/%m/%Y %H:%M'),
            'total': v.total,
            'ganancia_total': ganancia_total,
            'metodo_pago': v.get_metodo_pago_display(),
            'monto_recibido': v.monto_recibido,
            'vuelto': v.vuelto,
            'detalles': detalles
        })
    return JsonResponse({'ventas': data})


def api_listar_categorias(request):
    categorias = Categoria.objects.all().order_by('nombre')
    data = [{'id': c.id, 'nombre': c.nombre} for c in categorias]
    return JsonResponse({'categorias': data})

@csrf_exempt
def api_guardar_categoria(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nombre = data.get('nombre', '').strip()
            if not nombre:
                return JsonResponse({'success': False, 'error': 'El nombre de la categoría es requerido'})
            
            categoria, created = Categoria.objects.get_or_create(nombre=nombre)
            return JsonResponse({'success': True, 'categoria_id': categoria.id, 'nombre': categoria.nombre, 'mensaje': 'Categoría guardada'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
def descargar_bd(request):
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    if os.path.exists(db_path):
        return FileResponse(open(db_path, 'rb'), as_attachment=True, filename='db_backup.sqlite3')
    return JsonResponse({'error': 'Base de datos no encontrada'}, status=404)
