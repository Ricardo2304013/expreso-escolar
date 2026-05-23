from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Padre, Expreso, Estudiante, Asignacion, Incidencia

admin.site.site_header = "Expreso Escolar - Admin"
admin.site.site_title = "Expreso Escolar"
admin.site.index_title = "Panel de Administración"

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'first_name', 'last_name', 'email', 'rol', 'is_active']
    list_filter = ['rol', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Datos del Sistema', {'fields': ('rol',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos del Sistema', {'fields': ('first_name', 'last_name', 'email', 'rol')}),
    )

@admin.register(Padre)
class PadreAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'cedula', 'telefono']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'cedula']

@admin.register(Expreso)
class ExpresoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'placa', 'transportista', 'capacidad', 'cupos_disponibles', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'placa']

@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellido', 'curso', 'paralelo', 'estado', 'padre', 'expreso']
    list_filter = ['estado', 'curso']
    search_fields = ['nombre', 'apellido']

@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'expreso', 'tipo_servicio', 'estado', 'fecha_asignacion']
    list_filter = ['estado', 'tipo_servicio']

@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'expreso', 'reportado_por', 'fecha']
    list_filter = ['tipo']
