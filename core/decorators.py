from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def rol_requerido(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.rol not in roles:
                messages.error(request, 'No tienes permiso para acceder a esa página.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def solo_admin(view_func):
    return rol_requerido('admin')(view_func)


def solo_transportista(view_func):
    return rol_requerido('transportista')(view_func)


def solo_padre(view_func):
    return rol_requerido('padre')(view_func)


def admin_o_transportista(view_func):
    return rol_requerido('admin', 'transportista')(view_func)
