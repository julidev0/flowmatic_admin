import bcrypt
import openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from .models import Usuario


def login_view(request):
    if request.user.is_authenticated:
        return redirect('panel_admin')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('clave')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('panel_admin')
        else:
            messages.error(request, 'Credenciales inválidas o cuenta no activada.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def panel_admin(request):
    usuarios = Usuario.objects.all()

    total_usuarios = usuarios.count()
    rrhh_activos = usuarios.filter(rol='ROLE_RRHH', activo=True).count()
    candidatos = usuarios.filter(rol='ROLE_CANDIDATO').count()
    pendientes = usuarios.filter(rol='ROLE_CANDIDATO', activo=False).count()

    context = {
        'usuarios': usuarios,
        'total_usuarios': total_usuarios,
        'rrhh_activos': rrhh_activos,
        'candidatos': candidatos,
        'pendientes': pendientes,
    }
    return render(request, 'admin.html', context)


@login_required
def crear_rrhh(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if Usuario.objects.filter(email=email).exists():
            return HttpResponseRedirect(reverse('panel_admin') + '?error=duplicado')

        usuario = Usuario(
            username=request.POST.get('username'),
            apellido=request.POST.get('apellido'),
            email=email,
            clave=bcrypt.hashpw(
                request.POST.get('clave').encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8'),
            rol='ROLE_RRHH',
            activo=True,
        )
        usuario.save()
        return HttpResponseRedirect(reverse('panel_admin') + '?pendiente=1')

    return redirect('panel_admin')


@login_required
def eliminar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    usuario.delete()
    return redirect('panel_admin')


@login_required
def editar_usuario(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('id')
        usuario = get_object_or_404(Usuario, id=usuario_id)

        usuario.username = request.POST.get('username')
        usuario.apellido = request.POST.get('apellido')
        usuario.email = request.POST.get('email')
        usuario.telefono = request.POST.get('telefono') or None

        nueva_clave = request.POST.get('nuevaClave')
        if nueva_clave and nueva_clave.strip():
            usuario.clave = bcrypt.hashpw(
                nueva_clave.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')

        usuario.save()
        return HttpResponseRedirect(reverse('panel_admin') + '?editado=1')

    return redirect('panel_admin')


@login_required
def exportar_excel(request):
    usuarios = Usuario.objects.all()

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Usuarios'

    headers = ['ID', 'Username', 'Apellido', 'Email', 'Rol', 'Estado']
    for col, header in enumerate(headers, 1):
        sheet.cell(row=1, column=col, value=header)

    for row_idx, u in enumerate(usuarios, 2):
        sheet.cell(row=row_idx, column=1, value=u.id)
        sheet.cell(row=row_idx, column=2, value=u.username)
        sheet.cell(row=row_idx, column=3, value=u.apellido)
        sheet.cell(row=row_idx, column=4, value=u.email)
        sheet.cell(row=row_idx, column=5, value=u.rol)
        sheet.cell(row=row_idx, column=6, value='Activo' if u.activo else 'Pendiente')

    response = HttpResponse(
        content_type='application/octet-stream',
    )
    response['Content-Disposition'] = 'attachment; filename=usuarios_reporte.xlsx'
    workbook.save(response)
    return response
