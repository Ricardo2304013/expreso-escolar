from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('login/', views.vista_login, name='login'),
    path('registro/', views.vista_registro, name='registro'),
    path('logout/', views.vista_logout, name='logout'),
    # Estudiantes
    path('estudiantes/', views.lista_estudiantes, name='lista_estudiantes'),
    path('estudiantes/registrar/', views.registrar_estudiante, name='registrar_estudiante'),
    path('estudiantes/<int:pk>/retirar/', views.retirar_estudiante, name='retirar_estudiante'),
    path('estudiantes/<int:pk>/cambiar-expreso/', views.cambiar_expreso, name='cambiar_expreso'),
    # Expresos
    path('expresos/', views.lista_expresos, name='lista_expresos'),
    path('expresos/crear/', views.crear_expreso, name='crear_expreso'),
    path('expresos/<int:pk>/editar/', views.editar_expreso, name='editar_expreso'),
    path('expresos/<int:pk>/eliminar/', views.eliminar_expreso, name='eliminar_expreso'),
    # Asignaciones
    path('asignaciones/crear/', views.crear_asignacion, name='crear_asignacion'),
    path('asignaciones/<int:pk>/aceptar/', views.aceptar_asignacion, name='aceptar_asignacion'),
    path('asignaciones/<int:pk>/rechazar/', views.rechazar_asignacion, name='rechazar_asignacion'),
    # Incidencias
    path('incidencias/', views.lista_incidencias, name='lista_incidencias'),
    path('incidencias/reportar/', views.reportar_incidencia, name='reportar_incidencia'),
    # Usuarios
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    #Eliminar usuario 
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
    # Listados
    path('listados/expresos/', views.listado_por_expreso, name='listado_por_expreso'),
    path('listados/salones/', views.listado_por_salon, name='listado_por_salon'),
    path('listados/mis-salones/', views.listado_transportista_salones, name='listado_transportista_salones'),
    # Descargas
    path('listados/descargar/excel/', views.descargar_excel_completo, name='descargar_excel'),
    path('listados/descargar/mi-excel/', views.descargar_excel_transportista, name='descargar_excel_transportista'),
    path('listados/descargar/expreso/<int:expreso_id>/excel/', views.descargar_excel_un_expreso, name='descargar_excel_un_expreso'),
path('listados/descargar/expreso/<int:expreso_id>/salones/', views.descargar_excel_salones_expreso, name='descargar_excel_salones_expreso'),
]
