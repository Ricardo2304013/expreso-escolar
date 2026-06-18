from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

# DECORADOR GENÉRICO PARA VERIFICAR ROLES
def rol_requerido(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # PRIMERO: Verificar que el usuario está autenticado (logueado)
            if not request.user.is_authenticated:
                return redirect('login')
            # SEGUNDO: Verificar que el rol del usuario está entre los roles permitidos
            if request.user.rol not in roles:
                messages.error(request, 'No tienes permiso para acceder a esa página.')
                return redirect('dashboard')
            # Si pasa ambas verificaciones, ejecutar la vista original
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# DECORADORES ESPECÍFICOS PARA CADA ROL
def solo_admin(view_func):
    return rol_requerido('admin')(view_func)

# DECORADOR PARA PERMITIR SOLO A TRANSPORTISTAS
def solo_transportista(view_func):
    return rol_requerido('transportista')(view_func)

# DECORADOR PARA PERMITIR SOLO A PADRES
def solo_padre(view_func):
    return rol_requerido('padre')(view_func)

# DECORADOR PARA PERMITIR SOLO A ADMIN O TRANSPORTISTA
def admin_o_transportista(view_func):
    return rol_requerido('admin', 'transportista')(view_func)
