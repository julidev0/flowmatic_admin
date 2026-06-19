import uuid
import bcrypt
import openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError
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
        username = request.POST.get('username')
        if Usuario.objects.filter(email=email).exists():
            return HttpResponseRedirect(reverse('panel_admin') + '?error=duplicado')

        token = str(uuid.uuid4())
        usuario = Usuario(
            username=username,
            apellido=request.POST.get('apellido'),
            email=email,
            clave=bcrypt.hashpw(
                request.POST.get('clave').encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8'),
            rol='ROLE_RRHH',
            activo=False,
            tokenactivacion=token,
        )
        try:
            usuario.save()
        except IntegrityError:
            return HttpResponseRedirect(reverse('panel_admin') + '?error=duplicado')

        enlace = request.build_absolute_uri(f'/activar/?token={token}')
        asunto = 'Activa tu cuenta en FLOWMATIC'
        mensaje = f'''
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:32px;background:#f9f9f9;border-radius:12px;">
            <div style="text-align:center;margin-bottom:28px;">
                <h1 style="color:#0D9488;font-size:24px;margin:0;">FLOWMATIC</h1>
                <p style="color:#666;font-size:14px;">Gestión de Reclutamiento</p>
            </div>
            <div style="background:#fff;padding:32px;border-radius:8px;">
                <h2 style="color:#1a1a2e;font-size:18px;margin:0 0 12px;">Hola, {username}!</h2>
                <p style="color:#555;font-size:14px;line-height:1.6;">Te han registrado como personal RRHH en FLOWMATIC. Para activar tu cuenta, haz clic en el botón:</p>
                <div style="text-align:center;margin:28px 0;">
                    <a href="{enlace}" style="background:#0D9488;color:#fff;padding:14px 36px;border-radius:8px;text-decoration:none;font-size:15px;font-weight:600;display:inline-block;">Activar mi cuenta</a>
                </div>
                <p style="color:#999;font-size:12px;">Si no esperabas este correo, ignóralo.</p>
            </div>
        </div>
        '''
        send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [email], html_message=mensaje, fail_silently=False)

        return HttpResponseRedirect(reverse('panel_admin') + '?envio_exitoso=1')

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

        try:
            usuario.save()
        except IntegrityError:
            return HttpResponseRedirect(reverse('panel_admin') + '?error=duplicado')
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


def registro_candidato(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        apellido = request.POST.get('apellido')
        clave = request.POST.get('clave')
        telefono = request.POST.get('telefono') or None

        if Usuario.objects.filter(email=email).exists():
            return render(request, 'registro-candidato.html', {
                'error_duplicado': True,
            })

        token = str(uuid.uuid4())
        usuario = Usuario(
            username=username,
            apellido=apellido,
            email=email,
            clave=bcrypt.hashpw(clave.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            telefono=telefono,
            rol='ROLE_CANDIDATO',
            activo=False,
            tokenactivacion=token,
        )
        try:
            usuario.save()
        except IntegrityError:
            return render(request, 'registro-candidato.html', {
                'error_duplicado': True,
            })

        enlace = request.build_absolute_uri(f'/activar/?token={token}')
        asunto = 'Activa tu cuenta en FLOWMATIC'
        mensaje = f'''
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:32px;background:#f9f9f9;border-radius:12px;">
            <div style="text-align:center;margin-bottom:28px;">
                <h1 style="color:#0D9488;font-size:24px;margin:0;">FLOWMATIC</h1>
                <p style="color:#666;font-size:14px;">Gestión de Reclutamiento</p>
            </div>
            <div style="background:#fff;padding:32px;border-radius:8px;">
                <h2 style="color:#1a1a2e;font-size:18px;margin:0 0 12px;">Hola, {username}!</h2>
                <p style="color:#555;font-size:14px;line-height:1.6;">Gracias por registrarte. Para activar tu cuenta y empezar a usar FLOWMATIC, haz clic en el botón:</p>
                <div style="text-align:center;margin:28px 0;">
                    <a href="{enlace}" style="background:#0D9488;color:#fff;padding:14px 36px;border-radius:8px;text-decoration:none;font-size:15px;font-weight:600;display:inline-block;">Activar mi cuenta</a>
                </div>
                <p style="color:#999;font-size:12px;">Si no creaste esta cuenta, ignora este mensaje.</p>
            </div>
        </div>
        '''
        send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [email], html_message=mensaje, fail_silently=False)

        return redirect(f'{reverse("registro_candidato")}?pendiente=1')

    context = {
        'mensaje_pendiente': request.GET.get('pendiente') == '1',
    }
    return render(request, 'registro-candidato.html', context)


def activar_cuenta(request):
    token = request.GET.get('token')
    if not token:
        return render(request, 'activacion.html', {'token_invalido': True})

    try:
        usuario = Usuario.objects.get(tokenactivacion=token)
        usuario.activo = True
        usuario.tokenactivacion = None
        usuario.save()
        return render(request, 'activacion.html', {'activacion_exitosa': True})
    except Usuario.DoesNotExist:
        return render(request, 'activacion.html', {'token_invalido': True})
