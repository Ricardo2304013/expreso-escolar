from .models import AuditoriaLogin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Padre, Expreso, Estudiante, Asignacion, Incidencia

# Personaliza los textos que aparecen en el panel de administración de Django
admin.site.site_header = "Expreso Escolar - Admin" # Cabecera principal
admin.site.site_title = "Expreso Escolar"          # Título de la pestaña del navegador
admin.site.index_title = "Panel de Administración" # Título de la página principal

# REGISTRO Y CONFIGURACIÓN DEL MODELO USUARIO (EXTIENDE UserAdmin)
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # Campos visibles para usuarios
    list_display = ['username', 'first_name', 'last_name', 'email', 'rol', 'is_active']
    list_filter = ['rol', 'is_active']
    # Configuración de los campos al EDITAR un usuario (vista de detalle)
    fieldsets = UserAdmin.fieldsets + (
        ('Datos del Sistema', {'fields': ('rol',)}), # Añade 'rol' al final
    )
    # Configuración de los campos al CREAR un nuevo usuario
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos del Sistema', {'fields': ('first_name', 'last_name', 'email', 'rol')}),
    )

# REGISTRO Y CONFIGURACIÓN DEL MODELO PADRE
@admin.register(Padre)
class PadreAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'cedula', 'telefono']
    # Campos por los que se puede buscar (usando relaciones con __)
    search_fields = ['usuario__first_name', 'usuario__last_name', 'cedula']

# REGISTRO Y CONFIGURACIÓN DEL MODELO EXPRESO
@admin.register(Expreso)
class ExpresoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'placa', 'transportista', 'capacidad', 'cupos_disponibles', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'placa']

# REGISTRO Y CONFIGURACIÓN DEL MODELO ESTUDIANTE
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

@admin.register(AuditoriaLogin)
class AuditoriaLoginAdmin(admin.ModelAdmin):
    list_display  = ['fecha', 'accion', 'email_intento',
                     'usuario', 'ip', 'exitoso']
    list_filter   = ['accion', 'exitoso']
    search_fields = ['email_intento', 'ip']
    # Campos de solo lectura (no se pueden modificar desde el admin)
    readonly_fields = ['usuario', 'email_intento', 'accion',
                       'ip', 'navegador', 'fecha', 'exitoso']

    def has_add_permission(self, request):
        return False  # nadie puede crear registros manuales

    def has_delete_permission(self, request, obj=None): 
        return request.user.is_superuser  # solo superusuario elimina
