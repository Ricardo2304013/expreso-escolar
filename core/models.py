from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('transportista', 'Transportista'),
        ('padre', 'Padre de Familia'),
    ]
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='padre')
    telefono = models.CharField(max_length=15, blank=True)  # ← AGREGA ESTA LÍNEA

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_rol_display()})"

    def is_admin(self):
        return self.rol == 'admin'

    def is_transportista(self):
        return self.rol == 'transportista'

    def is_padre(self):
        return self.rol == 'padre'


class Padre(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='padre_perfil')
    cedula = models.CharField(max_length=13, unique=True)
    telefono = models.CharField(max_length=15)

    def __str__(self):
        return f"Padre: {self.usuario.get_full_name()}"

    class Meta:
        verbose_name = 'Padre de Familia'
        verbose_name_plural = 'Padres de Familia'


class Expreso(models.Model):
    transportista = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'rol': 'transportista'},
        related_name='expresos'
    )
    nombre = models.CharField(max_length=100)
    placa = models.CharField(max_length=10, unique=True)
    capacidad = models.PositiveIntegerField()
    cupos_disponibles = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.placa})"

    def porcentaje_ocupacion(self):
        if self.capacidad == 0:
            return 0
        ocupados = self.capacidad - self.cupos_disponibles
        return int((ocupados / self.capacidad) * 100)

    def cupos_ocupados(self):
        return self.capacidad - self.cupos_disponibles

    class Meta:
        verbose_name = 'Expreso'
        verbose_name_plural = 'Expresos'


class Estudiante(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('activo', 'Activo'),
        ('retirado', 'Retirado'),
        ('no_aceptado', 'No Aceptado'),
    ]
    CURSO_CHOICES = [
        ('Inicial', (
            ('Inicial 1', 'Inicial 1'),
            ('Inicial 2', 'Inicial 2'),
        )),
        ('Básica', (
            ('1ro Básica', '1ro Básica'),
            ('2do Básica', '2do Básica'),
            ('3ro Básica', '3ro Básica'),
            ('4to Básica', '4to Básica'),
            ('5to Básica', '5to Básica'),
            ('6to Básica', '6to Básica'),
            ('7mo Básica', '7mo Básica'),
        )),
        ('Media', (
            ('8vo Básica', '8vo Básica'),
            ('9no Básica', '9no Básica'),
            ('10mo Básica', '10mo Básica'),
        )),
        ('Bachillerato', (
            ('1ro Bachillerato', '1ro Bachillerato'),
            ('2do Bachillerato', '2do Bachillerato'),
            ('3ro Bachillerato', '3ro Bachillerato'),
        )),
    ]
    DIRECCION_CHOICES = [
        ('Mucho Lote', 'Mucho Lote'),
        ('Bastión Popular', 'Bastión Popular'),
        ('Mapasingue', 'Mapasingue'),
        ('Flor de Bastión', 'Flor de Bastión'),
        ('Monte Sinaí', 'Monte Sinaí'),
        ('Guasmo', 'Guasmo'),
        ('Prosperina', 'Prosperina'),
        ('Los Ceibos', 'Los Ceibos'),
        ('Urdesa', 'Urdesa'),
        ('Kennedy', 'Kennedy'),
        ('Otra', 'Otra dirección'),
    ]

    padre = models.ForeignKey(Padre, on_delete=models.CASCADE, related_name='estudiantes')
    expreso = models.ForeignKey(Expreso, on_delete=models.SET_NULL, null=True, blank=True, related_name='estudiantes')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    curso = models.CharField(max_length=50, choices=CURSO_CHOICES)          # ← ahora tiene choices
    paralelo = models.CharField(max_length=5)
    direccion = models.CharField(max_length=100, choices=DIRECCION_CHOICES, default='Mucho Lote') # ← reemplaza observacion
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
        ordering = ['-created_at']


class Asignacion(models.Model):
    TIPO_CHOICES = [
        ('medio', 'Medio Tiempo'),
        ('completo', 'Completo'),
    ]
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
    ]
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='asignaciones')
    expreso = models.ForeignKey(Expreso, on_delete=models.CASCADE, related_name='asignaciones')
    tipo_servicio = models.CharField(max_length=10, choices=TIPO_CHOICES, default='completo')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.estudiante} → {self.expreso} ({self.estado})"

    class Meta:
        verbose_name = 'Asignación'
        verbose_name_plural = 'Asignaciones'
        ordering = ['-fecha_asignacion']


class Incidencia(models.Model):
    TIPO_CHOICES = [
        ('accidente', 'Accidente'),
        ('retraso', 'Retraso'),
        ('mecanico', 'Problema Mecánico'),
        ('ausente', 'Estudiante Ausente'),
        ('otro', 'Otro'),
    ]
    TIPO_ICONS = {
        'accidente': '🚨',
        'retraso': '⏰',
        'mecanico': '🔧',
        'ausente': '👤',
        'otro': '📝',
    }
    expreso = models.ForeignKey(Expreso, on_delete=models.CASCADE, related_name='incidencias')
    reportado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField(max_length=500)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo} - {self.expreso} ({self.fecha.date()})"

    def icono(self):
        return self.TIPO_ICONS.get(self.tipo, '📝')

    class Meta:
        verbose_name = 'Incidencia'
        verbose_name_plural = 'Incidencias'
        ordering = ['-fecha']

class AuditoriaLogin(models.Model):
    ACCION_CHOICES = [
        ('login_exitoso',  'Login Exitoso'),
        ('login_fallido',  'Login Fallido'),
        ('logout',         'Cierre de Sesion'),
    ]
    usuario      = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='auditorias'
    )
    email_intento = models.CharField(
        max_length=254, blank=True,
        help_text='Correo que se intento usar'
    )
    accion       = models.CharField(max_length=20, choices=ACCION_CHOICES)
    ip           = models.GenericIPAddressField(null=True, blank=True)
    navegador    = models.CharField(max_length=300, blank=True)
    fecha        = models.DateTimeField(auto_now_add=True)
    exitoso      = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.accion} | {self.email_intento} | {self.fecha.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = 'Auditoria de Login'
        verbose_name_plural = 'Auditorias de Login'
        ordering = ['-fecha']