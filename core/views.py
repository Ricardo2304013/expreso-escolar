from .models import Usuario, Padre, Expreso, Estudiante, Asignacion, Incidencia, AuditoriaLogin
from .utils_excel import (generar_excel_completo, generar_excel_transportista,
                           generar_excel_un_expreso, generar_excel_salones_expreso,
                           generar_excel_un_salon, generar_excel_salon_profesor)
from .forms import (LoginForm, RegistroPadreForm, EstudianteForm, ExpresoForm,
                    AsignacionForm, AceptarAsignacionForm, IncidenciaForm,
                    UsuarioAdminForm, PadrePerfilForm)
import csv
from django.http import HttpResponse # Para enviar respuestas HTTP (descargas, etc.)
from django.core.paginator import Paginator # Para paginar listados largos
from django.db.models import Q # Para hacer búsquedas
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate # Autenticación de usuarios
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from .models import Usuario, Padre, Expreso, Estudiante, Asignacion, Incidencia
from .forms import (LoginForm, RegistroPadreForm, EstudianteForm, ExpresoForm,
                    AsignacionForm, AceptarAsignacionForm, IncidenciaForm, UsuarioAdminForm)
from .decorators import solo_admin, solo_transportista, solo_padre, admin_o_transportista

# ── OBTENER IP ──────────────────────────────────────────

def obtener_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        # Si hay múltiples IPs, tomamos la primera (la original del cliente)
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')

# ── AUTENTICACIÓN ──────────────────────────────────────────

def vista_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Inicializamos el formulario de login (vacio si es GET, con datos si es POST)
    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        email_intento = request.POST.get('username', '')
        ip            = obtener_ip(request)
        navegador     = request.META.get('HTTP_USER_AGENT', '')[:300]

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # ── Registrar login exitoso ──────────────
            AuditoriaLogin.objects.create(
                usuario       = user,
                email_intento = email_intento,
                accion        = 'login_exitoso',
                ip            = ip,
                navegador     = navegador,
                exitoso       = True,
            )
            messages.success(request,
                f'Bienvenido/a {user.first_name}.')
            return redirect('dashboard')
        else:
            # ── Registrar login fallido ──────────────
            # Intentar encontrar el usuario por email
            try:
                user_fallido = Usuario.objects.get(
                    username=email_intento)
            except Usuario.DoesNotExist:
                user_fallido = None

            AuditoriaLogin.objects.create(
                usuario       = user_fallido,
                email_intento = email_intento,
                accion        = 'login_fallido',
                ip            = ip,
                navegador     = navegador,
                exitoso       = False,
            )
    # Si es GET o el formulario no es válido, renderizamos la página de login con el formulario 
    return render(request, 'auth/login.html', {'form': form})

# Crea un usuario con rol 'padre' y su perfil asociado (Padre)
def vista_registro(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegistroPadreForm(request.POST or None) # Inicializamos el formulario con POST si es una solicitud POST, o vacío si es GET
    if request.method == 'POST' and form.is_valid(): # El usuario envió los datos y Validamos el formulario.
        # Limpiamos los datos validados
        d = form.cleaned_data
        # Creamos el usuario (username = email por simplicidad)
        user = Usuario.objects.create_user(
            username=d['email'], email=d['email'],
            password=d['password1'], first_name=d['nombre'],
            last_name=d['apellido'], rol='padre'
        )
        # Creamos el perfil de padre asociado a este usuario
        Padre.objects.create(usuario=user, cedula=d['cedula'], telefono=d['telefono'])
        # Autenticamos al usuario automáticamente después del registro
        login(request, user)
        messages.success(request, f'¡Bienvenido/a {user.first_name}! Tu cuenta fue creada correctamente.')
        return redirect('dashboard')
    # Si es GET o el formulario no es válido, mostramos el formulario de registro
    return render(request, 'auth/registro.html', {'form': form})

# Cierra la sesión del usuario actual y registra el evento en auditoría.
def vista_logout(request):
    if request.user.is_authenticated:
        AuditoriaLogin.objects.create(
            usuario       = request.user,
            email_intento = request.user.email,
            accion        = 'logout',
            ip            = obtener_ip(request),
            navegador     = request.META.get('HTTP_USER_AGENT', '')[:300],
            exitoso       = True,
        )
    logout(request)
    return redirect('login')


# ── DASHBOARD (redirige según rol) ────────────────────────

@login_required
def dashboard(request):
    if request.user.rol == 'admin':
        return dashboard_admin(request)
    elif request.user.rol == 'transportista':
        return dashboard_transportista(request)
    else:
        return dashboard_padre(request)


def dashboard_admin(request):
    expresos = Expreso.objects.all().select_related('transportista')
    estudiantes = Estudiante.objects.all()
    incidencias = Incidencia.objects.all().select_related('expreso', 'reportado_por')[:50]  # Últimas 50
    ultimos_estudiantes = estudiantes.order_by('-created_at')[:50]                          # Últimos 50 registrados

    ctx = {
        'total_estudiantes': estudiantes.count(),
        'activos': estudiantes.filter(estado='activo').count(),
        'pendientes': estudiantes.filter(estado='pendiente').count(),
        'retirados': estudiantes.filter(estado='retirado').count(),        # ← NUEVO
        'no_aceptados': estudiantes.filter(estado='no_aceptado').count(),  # ← NUEVO
        'expresos': expresos,
        'expresos_activos': expresos.filter(activo=True).count(),
        'total_padres': Padre.objects.count(),
        'incidencias': incidencias,
        'ultimos_estudiantes': ultimos_estudiantes,
    }
    return render(request, 'dashboard/admin.html', ctx)

# Muestra el expreso asignado, estudiantes activos y solicitudes pendientes.
def dashboard_transportista(request):
    # Buscamos el expreso asociado a este transportista
    try:
        expreso = Expreso.objects.get(transportista=request.user)
    except Expreso.DoesNotExist:
        expreso = None

    estudiantes_activos = []
    pendientes = []
    incidencias = []

    if expreso:
        # Estudiantes activos en este expreso
        estudiantes_activos = Estudiante.objects.filter(expreso=expreso, estado='activo').select_related('padre__usuario').prefetch_related('asignaciones')

        # Crear un diccionario estudiante_id -> tipo_servicio de la última asignación aceptada
        tipos_servicio = {}
        for est in estudiantes_activos:
            asig_aceptada = est.asignaciones.filter(expreso=expreso, estado='aceptado').order_by('-fecha_asignacion').first()
            tipos_servicio[est.pk] = asig_aceptada.tipo_servicio if asig_aceptada else 'completo'
        # Asignaciones pendientes de aceptar/rechazar
        pendientes = Asignacion.objects.filter(expreso=expreso, estado='pendiente').select_related('estudiante__padre__usuario')
        # Últimas 5 incidencias de este expreso
        incidencias = Incidencia.objects.filter(expreso=expreso)[:5]

    ctx = {
        'expreso': expreso,
        'estudiantes_activos': estudiantes_activos,
        'pendientes': pendientes,
        'incidencias': incidencias,
        'tipos_servicio': tipos_servicio if expreso else {},
    }
    return render(request, 'dashboard/transportista.html', ctx)


def dashboard_padre(request):
    try:
        padre = request.user.padre_perfil # Relación inversa OneToOne
        estudiantes = Estudiante.objects.filter(padre=padre).select_related('expreso__transportista')
    except Padre.DoesNotExist:
        padre = None
        estudiantes = []
    return render(request, 'dashboard/padre.html', {'estudiantes': estudiantes, 'padre': padre})


# ── ESTUDIANTES ───────────────────────────────────────────

@login_required
@solo_padre
def registrar_estudiante(request):
    padre = get_object_or_404(Padre, usuario=request.user) # Obtenemos el perfil de padre asociado al usuario actual. Si no existe, mostramos 404.
    form = EstudianteForm(request.POST or None) # Inicializamos el formulario con POST si es una solicitud POST, o vacío si es GET
    if request.method == 'POST' and form.is_valid():
        est = form.save(commit=False) # No guardamos aún porque necesitamos asignar el padre
        est.padre = padre # Padre registrando a un estudiante
        est.estado = 'pendiente' # Estado inicial: esperando asignación
        est.save()
        messages.success(request, f'Estudiante {est.nombre} {est.apellido} registrado. El administrador lo asignará pronto.')
        return redirect('dashboard')
    return render(request, 'estudiantes/form.html', {'form': form, 'titulo': 'Registrar Estudiante'})



@login_required
@solo_admin
def lista_estudiantes(request):
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')

     # Cargamos estudiantes con relaciones necesarias para evitar N+1 queries
    estudiantes = Estudiante.objects.all().select_related('padre__usuario', 'expreso')

    # Aplicar filtro de estado si está presente
    if estado:
        estudiantes = estudiantes.filter(estado=estado)

    # Aplicar búsqueda por nombre, apellido, padre, curso o paralelo
    if busqueda:
        estudiantes = estudiantes.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(padre__usuario__first_name__icontains=busqueda) |
            Q(padre__usuario__last_name__icontains=busqueda) |
            Q(curso__icontains=busqueda) |
            Q(paralelo__icontains=busqueda)
        )

    estudiantes = estudiantes.order_by('-created_at')

    paginator = Paginator(estudiantes, 15)  # 15 por página
    page = request.GET.get('page', 1)
    estudiantes_paginados = paginator.get_page(page)

    return render(request, 'estudiantes/lista.html', {
        'estudiantes': estudiantes_paginados,
        'estado_filtro': estado,
        'busqueda': busqueda,
        'total': paginator.count,
    })
# retirar estudiante 
@login_required
@solo_padre
def retirar_estudiante(request, pk):
    padre = get_object_or_404(Padre, usuario=request.user)
    est = get_object_or_404(Estudiante, pk=pk, padre=padre)
    if est.expreso:
        # Liberamos el cupo ocupado por este estudiante
        est.expreso.cupos_disponibles += 1
        est.expreso.save()
        est.expreso = None # Desvinculamos del expreso
    est.estado = 'retirado'
    est.save()
    messages.success(request, f'{est.nombre} fue retirado del servicio.')
    return redirect('dashboard')

#Cambiar de expreso (solo padres)
@login_required
@solo_padre
def cambiar_expreso(request, pk):
    padre = get_object_or_404(Padre, usuario=request.user)
    est = get_object_or_404(Estudiante, pk=pk, padre=padre, estado='activo')
    expresos_disponibles = Expreso.objects.filter(activo=True, cupos_disponibles__gt=0).exclude(pk=est.expreso.pk if est.expreso else 0)

    if request.method == 'POST':
        expreso_nuevo_id = request.POST.get('expreso_id')
        expreso_nuevo = get_object_or_404(Expreso, pk=expreso_nuevo_id, activo=True, cupos_disponibles__gt=0)

        # Liberar cupo del expreso anterior
        if est.expreso:
            est.expreso.cupos_disponibles += 1
            est.expreso.save()

        # Cancelar asignación anterior
        est.asignaciones.filter(estado='aceptado').update(estado='rechazado')

        # Crear nueva asignación pendiente
        Asignacion.objects.create(
            estudiante=est,
            expreso=expreso_nuevo,
            estado='pendiente',
            tipo_servicio='completo'
        )

        est.expreso = expreso_nuevo
        est.estado = 'pendiente'
        est.save()

        messages.success(request, f'{est.nombre} fue enviado al expreso "{expreso_nuevo.nombre}". El transportista debe aceptarlo.')
        return redirect('dashboard')

    return render(request, 'estudiantes/cambiar_expreso.html', {
        'estudiante': est,
        'expresos_disponibles': expresos_disponibles,
    })

# ── EXPRESOS ──────────────────────────────────────────────

@login_required
@solo_admin
def lista_expresos(request):
    busqueda = request.GET.get('q', '')
    filtro_estado = request.GET.get('estado', '')

    # Obtener todos los expresos de la BD
    expresos = Expreso.objects.all().select_related('transportista')

    # Búsqueda por nombre, placa o nombre del transportista
    if busqueda:
        expresos = expresos.filter(
            Q(nombre__icontains=busqueda) |
            Q(placa__icontains=busqueda) |
            Q(transportista__first_name__icontains=busqueda) |
            Q(transportista__last_name__icontains=busqueda)
        )
    # Filtro por estado
    if filtro_estado == 'activo':
        expresos = expresos.filter(activo=True)
    elif filtro_estado == 'inactivo':
        expresos = expresos.filter(activo=False)

    expresos = expresos.order_by('nombre')

    paginator = Paginator(expresos, 10)  # 10 por página
    page = request.GET.get('page', 1)
    expresos_paginados = paginator.get_page(page)

    #Enviar los datos a la plantilla HTML
    return render(request, 'expresos/lista.html', {
        'expresos': expresos_paginados,
        'busqueda': busqueda,
        'filtro_estado': filtro_estado,
        'total': paginator.count,
    })

# Crear nuevo expreso (solo admin)
@login_required
@solo_admin
def crear_expreso(request):
    form = ExpresoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        exp = form.save(commit=False)
        exp.cupos_disponibles = exp.capacidad # Al inicio, todos los cupos están libres
        exp.save()
        messages.success(request, f'Expreso "{exp.nombre}" creado correctamente.')
        return redirect('lista_expresos')
    return render(request, 'expresos/form.html', {'form': form, 'titulo': 'Crear Expreso'})

# Editar expreso existente (solo admin)
@login_required
@solo_admin
def editar_expreso(request, pk):
    exp = get_object_or_404(Expreso, pk=pk)
    form = ExpresoForm(request.POST or None, instance=exp)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Expreso actualizado.')
        return redirect('lista_expresos')
    return render(request, 'expresos/form.html', {'form': form, 'titulo': 'Editar Expreso'})

# Eliminar expreso (solo admin)
@login_required
@solo_admin
def eliminar_expreso(request, pk):
    exp = get_object_or_404(Expreso, pk=pk) 
    if request.method == 'POST': # Solo si confirma la eliminación
        exp.delete() # Borra de la BD
        messages.success(request, 'Expreso eliminado.')
    return redirect('lista_expresos')


# ── ASIGNACIONES ──────────────────────────────────────────

@login_required
@solo_admin
def crear_asignacion(request):
    tipo = request.GET.get('tipo', 'pendiente')
    if request.method == 'POST':
        tipo = request.POST.get('tipo_estudiante', 'pendiente')

    form = AsignacionForm(request.POST or None, tipo_estudiante=tipo)

    if request.method == 'POST' and form.is_valid():
        asig = form.save(commit=False)
        asig.estado = 'pendiente'
        asig.save()
        # Si era no_aceptado, limpiar estado anterior y reasignar expreso
        asig.estudiante.expreso = asig.expreso
        asig.estudiante.estado = 'pendiente'
        asig.estudiante.save()
        messages.success(request, f'Asignación creada para {asig.estudiante}. El transportista debe aceptarla.')
        return redirect('lista_estudiantes')
    
    # Contamos estudiantes en cada estado para mostrar en la plantilla
    pendientes_count   = Estudiante.objects.filter(estado='pendiente').count()
    no_aceptados_count = Estudiante.objects.filter(estado='no_aceptado').count()

    return render(request, 'asignaciones/form.html', {
        'form': form,
        'tipo': tipo,
        'pendientes_count': pendientes_count,
        'no_aceptados_count': no_aceptados_count,
    })

# Aceptar asignación (solo transportista, solo pendientes)
@login_required
@solo_transportista
def aceptar_asignacion(request, pk):
    asig = get_object_or_404(Asignacion, pk=pk, expreso__transportista=request.user, estado='pendiente')
    form = AceptarAsignacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        asig.tipo_servicio = form.cleaned_data['tipo_servicio']
        asig.estado = 'aceptado'
        asig.save()
        # Actualizar estudiante
        asig.estudiante.estado = 'activo'
        asig.estudiante.save()
        # Ocupar un cupo en el expreso
        asig.expreso.cupos_disponibles = max(0, asig.expreso.cupos_disponibles - 1)
        asig.expreso.save()
        messages.success(request, f'{asig.estudiante} fue aceptado en el expreso.')
        return redirect('dashboard')
    return render(request, 'asignaciones/aceptar.html', {'asig': asig, 'form': form})

# Rechazar asignación (solo transportista, solo pendientes)
@login_required
@solo_transportista
def rechazar_asignacion(request, pk):
    asig = get_object_or_404(Asignacion, pk=pk, expreso__transportista=request.user, estado='pendiente')
    if request.method == 'POST':
        asig.estado = 'rechazado'
        asig.save()
        asig.estudiante.estado = 'no_aceptado'
        asig.estudiante.expreso = None
        asig.estudiante.save()
        messages.warning(request, f'Asignación de {asig.estudiante} rechazada.')
    return redirect('dashboard')


# ── INCIDENCIAS ───────────────────────────────────────────

@login_required
@solo_transportista
def reportar_incidencia(request):
    try:
        expreso = Expreso.objects.get(transportista=request.user)
    except Expreso.DoesNotExist:
        messages.error(request, 'No tienes un expreso asignado.')
        return redirect('dashboard')
    form = IncidenciaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        inc = form.save(commit=False)
        inc.expreso = expreso
        inc.reportado_por = request.user
        inc.save()
        messages.success(request, 'Incidencia reportada correctamente.')
        return redirect('dashboard')
    return render(request, 'incidencias/form.html', {'form': form, 'expreso': expreso})

# Lista de incidencias (solo admin)
@login_required
@solo_admin
def lista_incidencias(request):
    incidencias = Incidencia.objects.all().select_related('expreso', 'reportado_por')
    return render(request, 'incidencias/lista.html', {'incidencias': incidencias})


# ── USUARIOS (admin) ──────────────────────────────────────

@login_required
@solo_admin
def lista_usuarios(request):
    admins        = Usuario.objects.filter(rol='admin').order_by('first_name')
    transportistas = Usuario.objects.filter(rol='transportista').order_by('first_name')
    padres        = Usuario.objects.filter(rol='padre').order_by('first_name')
    return render(request, 'usuarios/lista.html', {
        'admins': admins,
        'transportistas': transportistas,
        'padres': padres,
    })

# Crear nuevo usuario (solo admin)
@login_required
@solo_admin
def crear_usuario(request):
    form = UsuarioAdminForm(request.POST or None)
    padre_form = None
 
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.username = form.cleaned_data['email']
        pw = form.cleaned_data.get('password1')
        if pw:
            user.set_password(pw)
        else:
            user.set_unusable_password()
        user.save()
 
        if user.rol == 'padre':
            Padre.objects.get_or_create(
                usuario=user,
                defaults={'cedula': '-', 'telefono': '-'}
            )
 
        messages.success(request, f'Usuario {user.get_full_name()} creado.')
        return redirect('lista_usuarios')
 
    return render(request, 'usuarios/form.html', {
        'form': form,
        'padre_form': padre_form,
        'titulo': 'Crear Usuario',
    })
    form = UsuarioAdminForm(request.POST or None)
    padre_form = None

    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.username = form.cleaned_data['email']
        pw = form.cleaned_data.get('password1')
        if pw:
            user.set_password(pw)
        else:
            user.set_unusable_password()
        user.save()

        if user.rol == 'padre':
            Padre.objects.get_or_create(
                usuario=user,
                defaults={'cedula': '-', 'telefono': '-'}
            )

        messages.success(request, f'Usuario {user.get_full_name()} creado.')
        return redirect('lista_usuarios')

    return render(request, 'usuarios/form.html', {
        'form': form,
        'padre_form': padre_form,
        'titulo': 'Crear Usuario',
    })
    form = UsuarioAdminForm(request.POST or None)
    padre_form = None

    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.username = form.cleaned_data['email']
        pw = form.cleaned_data.get('password1')
        if pw:
            user.set_password(pw)
        else:
            user.set_unusable_password()
        user.save()

        if user.rol == 'padre':
            Padre.objects.get_or_create(
                usuario=user,
                defaults={'cedula': '—', 'telefono': '—'}
            )

        messages.success(request, f'Usuario {user.get_full_name()} creado.')
        return redirect('lista_usuarios')

    return render(request, 'usuarios/form.html', {
        'form': form,
        'padre_form': padre_form,
        'titulo': 'Crear Usuario',
    })

# Editar usuario existente (solo admin)
@login_required
@solo_admin
def editar_usuario(request, pk):
    user = get_object_or_404(Usuario, pk=pk)
    form = UsuarioAdminForm(request.POST or None, instance=user)

    padre_form = None
    if user.rol == 'padre':
        padre_perfil, _ = Padre.objects.get_or_create(
            usuario=user,
            defaults={'cedula': '—', 'telefono': '—'}
        )
        padre_form = PadrePerfilForm(request.POST or None, instance=padre_perfil)

    if request.method == 'POST':
        forms_validos = form.is_valid()
        if padre_form:
            forms_validos = forms_validos and padre_form.is_valid()

        if forms_validos:
            user = form.save(commit=False)
            user.username = form.cleaned_data['email']
            pw = form.cleaned_data.get('password1')
            if pw:
                user.set_password(pw)
            user.save()

            if padre_form:
                padre_form.save()

            messages.success(request, f'Usuario {user.get_full_name()} actualizado.')
            return redirect('lista_usuarios')

    return render(request, 'usuarios/form.html', {
        'form': form,
        'padre_form': padre_form,
        'titulo': 'Editar Usuario',
    })
    user = get_object_or_404(Usuario, pk=pk)
    form = UsuarioAdminForm(request.POST or None, instance=user)

    # Si es padre, cargamos también su perfil de Padre
    padre_form = None
    if user.rol == 'padre':
        padre_perfil, _ = Padre.objects.get_or_create(
            usuario=user,
            defaults={'cedula': '—', 'telefono': '—'}
        )
        padre_form = PadrePerfilForm(request.POST or None, instance=padre_perfil)

    if request.method == 'POST':
        forms_validos = form.is_valid()
        if padre_form:
            forms_validos = forms_validos and padre_form.is_valid()

        if forms_validos:
            user = form.save(commit=False)
            user.username = form.cleaned_data['email']
            pw = form.cleaned_data.get('password1')
            if pw:
                user.set_password(pw)
            user.save()

            if padre_form:
                padre_form.save()

            messages.success(request, f'Usuario {user.get_full_name()} actualizado.')
            return redirect('lista_usuarios')

    return render(request, 'usuarios/form.html', {
        'form': form,
        'padre_form': padre_form,
        'titulo': 'Editar Usuario',
    })
    

# Eliminar usuario (solo admin, no puede eliminarse a sí mismo)
@login_required
@solo_admin
def eliminar_usuario(request, pk):
    user = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'No puedes eliminar tu propio usuario.')
            return redirect('lista_usuarios')
        user.delete()
        messages.success(request, f'Usuario eliminado correctamente.')
    return redirect('lista_usuarios')

# ── LISTADOS ──────────────────────────────────────────────
@login_required
@solo_admin
def listado_por_expreso(request):
    ORDEN_CURSOS = [
        'Inicial 1', 'Inicial 2',
        '1ro Básica', '2do Básica', '3ro Básica', '4to Básica',
        '5to Básica', '6to Básica', '7mo Básica',
        '8vo Básica', '9no Básica', '10mo Básica',
        '1ro Bachillerato', '2do Bachillerato', '3ro Bachillerato',
    ]

    expresos = Expreso.objects.filter(activo=True).select_related('transportista')
    expresos_data = []

    for exp in expresos:
        # ← CAMBIO CLAVE: usar Estudiante.objects directamente
        estudiantes = list(
            Estudiante.objects.filter(expreso=exp, estado='activo')
            .select_related('padre__usuario')
            .order_by('apellido')
        )

        if not estudiantes:
            continue

        # Agrupar por curso → paralelo
        cursos_dict = {}
        for est in estudiantes:
            if est.curso not in cursos_dict:
                cursos_dict[est.curso] = {}
            if est.paralelo not in cursos_dict[est.curso]:
                cursos_dict[est.curso][est.paralelo] = []
            cursos_dict[est.curso][est.paralelo].append(est)

        # Ordenar cursos según ORDEN_CURSOS
        cursos_ordenados = []
        for curso in ORDEN_CURSOS:
            if curso not in cursos_dict:
                continue
            paralelos = []
            for paralelo in sorted(cursos_dict[curso].keys()):
                paralelos.append({
                    'paralelo': paralelo,
                    'estudiantes': sorted(
                        cursos_dict[curso][paralelo],
                        key=lambda e: e.apellido
                    )
                })
            cursos_ordenados.append({
                'curso': curso,
                'paralelos': paralelos,
            })

        expresos_data.append({
            'exp': exp,
            'cursos': cursos_ordenados,
            'total': len(estudiantes),
        })

    tab_activo = request.GET.get('tab', 'todos')
    return render(request, 'listados/admin_por_expreso.html', {
        'expresos_data': expresos_data,
        'tab_activo': tab_activo,
    })

# Listado por salón (agrupado por curso-paralelo, sin importar el expreso)
@login_required
@solo_admin
def listado_por_salon(request):
    # Obtener todos los cursos únicos que tienen estudiantes activos
    cursos = Estudiante.objects.filter(estado='activo').values_list('curso', 'paralelo').distinct().order_by('curso', 'paralelo')
    salones = []
    for curso, paralelo in cursos:
        estudiantes = Estudiante.objects.filter(
            estado='activo', curso=curso, paralelo=paralelo
        ).select_related('expreso__transportista', 'padre__usuario').order_by('expreso__nombre', 'apellido')
        # Expresos distintos que tienen estudiantes en este salón
        expresos_en_salon = Expreso.objects.filter(
            estudiantes__curso=curso,
            estudiantes__paralelo=paralelo,
            estudiantes__estado='activo'
        ).distinct()
        salones.append({
            'curso': curso,
            'paralelo': paralelo,
            'nombre': f"{curso} \"{paralelo}\"",
            'estudiantes': estudiantes,
            'expresos': expresos_en_salon,
            'total': estudiantes.count(),
        })
    return render(request, 'listados/admin_por_salon.html', {'salones': salones})

# Listado de salones para un transportista específico (solo muestra los salones que tienen estudiantes de su expreso)
@login_required
@solo_transportista
def listado_transportista_salones(request):
    try:
        expreso = Expreso.objects.get(transportista=request.user)
    except Expreso.DoesNotExist:
        messages.error(request, 'No tienes un expreso asignado.')
        return redirect('dashboard')
    # Agrupar estudiantes activos por salón
    cursos = Estudiante.objects.filter(
        expreso=expreso, estado='activo'
    ).values_list('curso', 'paralelo').distinct().order_by('curso', 'paralelo')
    salones = []
    for curso, paralelo in cursos:
        estudiantes = Estudiante.objects.filter(
            expreso=expreso, estado='activo', curso=curso, paralelo=paralelo
        ).select_related('padre__usuario').order_by('apellido')
        salones.append({
            'nombre': f"{curso} \"{paralelo}\"",
            'curso': curso,
            'paralelo': paralelo,
            'estudiantes': estudiantes,
            'total': estudiantes.count(),
        })
    return render(request, 'listados/transportista_salones.html', {
        'expreso': expreso,
        'salones': salones,
        'total_estudiantes': Estudiante.objects.filter(expreso=expreso, estado='activo').count(),
    })


# ── DESCARGAS CSV ─────────────────────────────────────────
from .utils_excel import (generar_excel_completo, generar_excel_transportista,
                           generar_excel_un_expreso, generar_excel_salones_expreso)

# Descargar Excel completo (solo admin)
@login_required
@solo_admin
def descargar_excel_completo(request):
    expresos = Expreso.objects.filter(activo=True).select_related('transportista')
    return generar_excel_completo(expresos)

# Descargar Excel de un transportista (solo transportista, solo su expreso)
@login_required
@solo_transportista
def descargar_excel_transportista(request):
    try:
        expreso = Expreso.objects.get(transportista=request.user)
    except Expreso.DoesNotExist:
        messages.error(request, 'No tienes un expreso asignado.')
        return redirect('dashboard')
    return generar_excel_transportista(expreso)

# Descargar Excel de un expreso específico (solo admin)
@login_required
@solo_admin
def descargar_excel_un_expreso(request, expreso_id):
    expreso = get_object_or_404(Expreso, pk=expreso_id)
    return generar_excel_un_expreso(expreso)

# Descargar Excel de los salones de un expreso específico (solo admin)
@login_required
@solo_admin
def descargar_excel_salones_expreso(request, expreso_id):
    expreso = get_object_or_404(Expreso, pk=expreso_id)
    return generar_excel_salones_expreso(expreso)

# Descargar Excel de un salón específico (solo admin)
@login_required
@solo_admin
def lista_auditoria(request):
    busqueda = request.GET.get('q', '')
    filtro   = request.GET.get('accion', '')

    registros = AuditoriaLogin.objects.select_related('usuario')

    if busqueda:
        registros = registros.filter(
            Q(email_intento__icontains=busqueda) |
            Q(ip__icontains=busqueda)
        )
    if filtro:
        registros = registros.filter(accion=filtro)

    paginator = Paginator(registros, 20)
    page      = request.GET.get('page', 1)

    return render(request, 'auditoria/lista.html', {
        'registros': paginator.get_page(page),
        'total':     paginator.count,
        'busqueda':  busqueda,
        'filtro':    filtro,
    })

# Descargar Excel de un salón específico (solo admin)
@login_required
@solo_admin
def descargar_excel_salon(request, expreso_id):
    expreso = get_object_or_404(Expreso, pk=expreso_id)
    curso   = request.GET.get('curso', '')
    paralelo = request.GET.get('paralelo', '')
    return generar_excel_un_salon(expreso, curso, paralelo)

# Descargar Excel de un salón específico para un transportista (solo muestra su expreso)
@login_required
@solo_transportista
def descargar_excel_salon_transportista(request, expreso_id):
    expreso = get_object_or_404(Expreso, pk=expreso_id, transportista=request.user)
    curso    = request.GET.get('curso', '')
    paralelo = request.GET.get('paralelo', '')
    return generar_excel_un_salon(expreso, curso, paralelo)

# Descargar Excel para profesores 
@login_required
@solo_admin
def descargar_excel_salon_profesor(request):
    curso = request.GET.get('curso', '')
    paralelo = request.GET.get('paralelo', '')
    return generar_excel_salon_profesor(curso, paralelo)