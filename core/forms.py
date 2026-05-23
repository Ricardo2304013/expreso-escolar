from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Usuario, Padre, Estudiante, Expreso, Asignacion, Incidencia


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Correo electrónico',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'})
    )


class RegistroPadreForm(forms.Form):
    nombre = forms.CharField(label='Nombre', max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido = forms.CharField(label='Apellido', max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control'}))
    cedula = forms.CharField(label='Cédula', max_length=13,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    telefono = forms.CharField(label='Teléfono', max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError('Este correo ya está registrado.')
        return email

    def clean_cedula(self):
        cedula = self.cleaned_data['cedula']
        if Padre.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError('Esta cédula ya está registrada.')
        return cedula

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')
        return cleaned_data


class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = ['nombre', 'apellido', 'curso', 'paralelo', 'direccion']
        labels = {
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'curso': 'Curso / Grado',
            'paralelo': 'Paralelo',
            'direccion': 'Dirección / Sector',
        }
        widgets = {
            'nombre':    forms.TextInput(attrs={'class': 'form-control'}),
            'apellido':  forms.TextInput(attrs={'class': 'form-control'}),
            'curso':     forms.Select(attrs={'class': 'form-select'}),
            'paralelo':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: A'}),
            'direccion': forms.Select(attrs={'class': 'form-select'}),
        }


class ExpresoForm(forms.ModelForm):
    class Meta:
        model = Expreso
        fields = ['nombre', 'placa', 'capacidad', 'transportista', 'activo']
        labels = {
            'nombre': 'Nombre del Expreso', 'placa': 'Placa del Vehículo',
            'capacidad': 'Capacidad Máxima', 'transportista': 'Transportista Asignado',
            'activo': 'Activo',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'placa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: ABC-1234'}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'transportista': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transportista'].queryset = Usuario.objects.filter(rol='transportista', is_active=True)


class AsignacionForm(forms.ModelForm):
    TIPO_ESTUDIANTE = [
        ('pendiente', 'Estudiantes Pendientes'),
        ('no_aceptado', 'Estudiantes No Aceptados'),
    ]
    tipo_estudiante = forms.ChoiceField(
        choices=TIPO_ESTUDIANTE,
        label='Tipo de estudiante',
        initial='pendiente',
        widget=forms.RadioSelect(attrs={'class': 'radio-group'}),
        required=False,
    )

    class Meta:
        model = Asignacion
        fields = ['estudiante', 'expreso']
        labels = {'estudiante': 'Estudiante', 'expreso': 'Expreso'}
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-select'}),
            'expreso': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        tipo = kwargs.pop('tipo_estudiante', 'pendiente')
        super().__init__(*args, **kwargs)
        if tipo == 'no_aceptado':
            self.fields['estudiante'].queryset = Estudiante.objects.filter(estado='no_aceptado')
        else:
            self.fields['estudiante'].queryset = Estudiante.objects.filter(estado='pendiente', expreso__isnull=True)  # ← solo sin expreso asignado
        self.fields['expreso'].queryset = Expreso.objects.filter(activo=True, cupos_disponibles__gt=0)


class AceptarAsignacionForm(forms.Form):
    tipo_servicio = forms.ChoiceField(
        choices=[('medio', 'Medio Tiempo'), ('completo', 'Completo')],
        label='Tipo de Servicio',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class IncidenciaForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ['tipo', 'descripcion']
        labels = {'tipo': 'Tipo de Incidencia', 'descripcion': 'Descripción'}
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                'placeholder': 'Describa la incidencia en detalle...', 'maxlength': 500}),
        }


class UsuarioAdminForm(forms.ModelForm):
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'rol', 'telefono', 'is_active']  # ← sin 'username'
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
            'rol': 'Rol',
            'telefono': 'Teléfono',
            'is_active': 'Activo',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 0991234567'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        # Verificar que el email no esté en uso por otro usuario
        qs = Usuario.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Este correo ya está registrado.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return cleaned
