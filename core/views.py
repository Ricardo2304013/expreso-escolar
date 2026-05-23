from .utils_excel import generar_excel_completo
import csv
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from .models import Usuario, Padre, Expreso, Estudiante, Asignacion, Incidencia
from .forms import (LoginForm, RegistroPadreForm, EstudianteForm, ExpresoForm,
                    AsignacionForm, AceptarAsignacionForm, IncidenciaForm, UsuarioAdminForm)
from .decorators import solo_admin, solo_transportista, solo_padre, admin_o_transportista


# ── AUTENTICACIÓN ──────────────────────────────────────────

def vista_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('dashboard')
    return render(request, 'auth/login.html', {'form': form})


def vista_registro(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegistroPadreForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        user = Usuario.objects.create_user(
            username=d['email'], email=d['email'],
            password=d['password1'], first_name=d['nombre'],
            last_name=d['apellido'], rol='padre'
        )
        Padre.objects.create(usuario=user, cedula=d['cedula'], telefono=d['telefono'])
        login(request, user)
        messages.success(request, f'¡Bienvenido/a {user.first_name}! Tu cuenta fue creada correctamente.')
        return redirect('dashboard')
    return render(request, 'auth/registro.html', {'form': form})


def vista_logout(request):
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
    incidencias = Incidencia.objects.all().select_related('expreso', 'reportado_por')[:50]  # antes :10
    ultimos_estudiantes = estudiantes.order_by('-created_at')[:50]                          # antes :5

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


def dashboard_transportista(request):
    try:
        expreso = Expreso.objects.get(transportista=request.user)
    except Expreso.DoesNotExist:
        expreso = None

    estudiantes_activos = []
    pendientes = []
    incidencias = []

    if expreso:
        estudiantes_activos = Estudiante.objects.filter(expreso=expreso, estado='activo').select_related('padre__usuario')
        pendientes = Asignacion.objects.filter(expreso=expreso, estado='pendiente').select_related('estudiante__padre__usuario')
        incidencias = Incidencia.objects.filter(expreso=expreso)[:5]

    ctx = {
        'expreso': expreso,
        'estudiantes_activos': estudiantes_activos,
        'pendientes': pendientes,
        'incidencias': incidencias,
    }
    return render(request, 'dashboard/transportista.html', ctx)


def dashboard_padre(request):
    try:
        padre = request.user.padre_perfil
        estudiantes = Estudiante.objects.filter(padre=padre).select_related('expreso__transportista')
    except Padre.DoesNotExist:
        padre = None
        estudiantes = []
    return render(request, 'dashboard/padre.html', {'estudiantes': estudiantes, 'padre': padre})


# ── ESTUDIANTES ───────────────────────────────────────────

@login_required
@solo_padre
def registrar_estudiante(request):
    padre = get_object_or_404(Padre, usuario=request.user)
    form = EstudianteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        est = form.save(commit=False)
        est.padre = padre
        est.estado = 'pendiente'
        est.save()
        messages.success(request, f'Estudiante {est.nombre} {est.apellido} registrado. El administrador lo asignará pronto.')
        return redirect('dashboard')
    return render(request, 'estudiantes/form.html', {'form': form, 'titulo': 'Registrar Estudiante'})



@login_required
@solo_admin
def lista_estudiantes(request):
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')

    estudiantes = Estudiante.objects.all().select_related('padre__usuario', 'expreso')

    if estado:
        estudiantes = estudiantes.filter(estado=estado)

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

@login_required
@solo_padre
def retirar_estudiante(request, pk):
    padre = get_object_or_404(Padre, usuario=request.user)
    est = get_object_or_404(Estudiante, pk=pk, padre=padre)
    if est.expreso:
        est.expreso.cupos_disponibles += 1
        est.expreso.save()
        est.expreso = None
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

    expresos = Expreso.objects.all().select_related('transportista')

    if busqueda:
        expresos = expresos.filter(
            Q(nombre__icontains=busqueda) |
            Q(placa__icontains=busqueda) |
            Q(transportista__first_name__icontains=busqueda) |
            Q(transportista__last_name__icontains=busqueda)
        )

    if filtro_estado == 'activo':
        expresos = expresos.filter(activo=True)
    elif filtro_estado == 'inactivo':
        expresos = expresos.filter(activo=False)

    expresos = expresos.order_by('nombre')

    paginator = Paginator(expresos, 10)  # 10 por página
    page = request.GET.get('page', 1)
    expresos_paginados = paginator.get_page(page)

    return render(request, 'expresos/lista.html', {
        'expresos': expresos_paginados,
        'busqueda': busqueda,
        'filtro_estado': filtro_estado,
        'total': paginator.count,
    })


@login_required
@solo_admin
def crear_expreso(request):
    form = ExpresoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        exp = form.save(commit=False)
        exp.cupos_disponibles = exp.capacidad
        exp.save()
        messages.success(request, f'Expreso "{exp.nombre}" creado correctamente.')
        return redirect('lista_expresos')
    return render(request, 'expresos/form.html', {'form': form, 'titulo': 'Crear Expreso'})


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


@login_required
@solo_admin
def eliminar_expreso(request, pk):
    exp = get_object_or_404(Expreso, pk=pk)
    if request.method == 'POST':
        exp.delete()
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

    pendientes_count   = Estudiante.objects.filter(estado='pendiente').count()
    no_aceptados_count = Estudiante.objects.filter(estado='no_aceptado').count()

    return render(request, 'asignaciones/form.html', {
        'form': form,
        'tipo': tipo,
        'pendientes_count': pendientes_count,
        'no_aceptados_count': no_aceptados_count,
    })


@login_required
@solo_transportista
def aceptar_asignacion(request, pk):
    asig = get_object_or_404(Asignacion, pk=pk, expreso__transportista=request.user, estado='pendiente')
    form = AceptarAsignacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        asig.tipo_servicio = form.cleaned_data['tipo_servicio']
        asig.estado = 'aceptado'
        asig.save()
        asig.estudiante.estado = 'activo'
        asig.estudiante.save()
        asig.expreso.cupos_disponibles = max(0, asig.expreso.cupos_disponibles - 1)
        asig.expreso.save()
        messages.success(request, f'{asig.estudiante} fue aceptado en el expreso.')
        return redirect('dashboard')
    return render(request, 'asignaciones/aceptar.html', {'asig': asig, 'form': form})


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


@login_required
@solo_admin
def crear_usuario(request):
    form = UsuarioAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        # Hacer que el username siempre sea igual al email
        user.username = form.cleaned_data['email']
        pw = form.cleaned_data.get('password1')
        if pw:
            user.set_password(pw)
        else:
            user.set_unusable_password()
        user.save()
        # Si es padre, crear perfil automáticamente
        if user.rol == 'padre':
            from .models import Padre
            if not hasattr(user, 'padre_perfil'):
                Padre.objects.get_or_create(
                    usuario=user,
                    defaults={'cedula': '—', 'telefono': '—'}
                )
        messages.success(request, f'Usuario {user.get_full_name()} creado. Puede ingresar con su correo.')
        return redirect('lista_usuarios')
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Crear Usuario'})

@login_required
@solo_admin
def editar_usuario(request, pk):
    user = get_object_or_404(Usuario, pk=pk)
    form = UsuarioAdminForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        # Sincronizar username con email siempre
        user.username = form.cleaned_data['email']
        pw = form.cleaned_data.get('password1')
        if pw:
            user.set_password(pw)
        user.save()
        messages.success(request, f'Usuario {user.get_full_name()} actualizado.')
        return redirect('lista_usuarios')
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Editar Usuario'})

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

@login_required
@solo_admin
def descargar_excel_completo(request):
    expresos = Expreso.objects.filter(activo=True).select_related('transportista')
    return generar_excel_completo(expresos)


@login_required
@solo_transportista
def descargar_excel_transportista(request):
    try:
        expreso = Expreso.objects.get(transportista=request.user)
    except Expreso.DoesNotExist:
        messages.error(request, 'No tienes un expreso asignado.')
        return redirect('dashboard')
    return generar_excel_transportista(expreso)

@login_required
@solo_admin
def descargar_excel_un_expreso(request, expreso_id):
    expreso = get_object_or_404(Expreso, pk=expreso_id)
    return generar_excel_un_expreso(expreso)


@login_required
@solo_admin
def descargar_excel_salones_expreso(request, expreso_id):
    expreso = get_object_or_404(Expreso, pk=expreso_id)
    return generar_excel_salones_expreso(expreso)