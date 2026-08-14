from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/producto/guardar/', views.api_guardar_producto, name='api_guardar_producto'),
    path('api/producto/<str:codigo>/', views.api_buscar_producto, name='api_buscar_producto'),
    path('api/venta/procesar/', views.api_procesar_venta, name='api_procesar_venta'),
    path('api/inventario/', views.api_listar_inventario, name='api_listar_inventario'),
    path('api/producto/eliminar/<int:id>/', views.api_eliminar_producto, name='api_eliminar_producto'),
    path('api/ventas/historial/', views.api_historial_ventas, name='api_historial_ventas'),
    path('db/descargar/', views.descargar_bd, name='descargar_bd'),
]
