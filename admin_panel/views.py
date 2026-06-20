import os
import uuid
import bcrypt
import smtplib
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError
from django.urls import reverse
from .models import Usuario
from django.db.models import Q

def login_view(request):
    if request.user.is_authenticated:
        return redirect('panel_admin')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('clave', '')
        if not email or not password:
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'login.html')
        try:
            user = authenticate(request, email=email, password=password)
        except Exception:
            messages.error(request, 'Error al iniciar sesión. Intenta de nuevo.')
            return render(request, 'login.html')
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
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        clave = request.POST.get('clave', '')

        if not email or not username or not apellido or not clave:
            return HttpResponseRedirect(reverse('panel_admin') + '?error=campos_vacios')
        if len(clave) < 8:
            return HttpResponseRedirect(reverse('panel_admin') + '?error=clave_corta')

        if Usuario.objects.filter(email=email).exists():
            return redirect('/admin/?error=duplicado')

        token = str(uuid.uuid4())
        try:
            usuario = Usuario(
                username=username,
                apellido=apellido,
                email=email,
                clave=bcrypt.hashpw(clave.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                rol='ROLE_RRHH',
                activo=False,
                tokenactivacion=token,
            )
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
        try:
            send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [email], html_message=mensaje, fail_silently=False)
        except smtplib.SMTPException:
            return HttpResponseRedirect(reverse('panel_admin') + '?envio_exitoso=1&email_fallo=1')

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
        if not usuario_id:
            return redirect('panel_admin')

        usuario = get_object_or_404(Usuario, id=usuario_id)

        username = request.POST.get('username', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        email = request.POST.get('email', '').strip()

        if not username or not apellido or not email:
            return HttpResponseRedirect(reverse('panel_admin') + '?error=campos_vacios')

        usuario.username = username
        usuario.apellido = apellido
        usuario.email = email
        usuario.telefono = request.POST.get('telefono', '').strip() or None

        nueva_clave = request.POST.get('nuevaClave', '')
        if nueva_clave and len(nueva_clave) >= 8:
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
    try:
        cols_seleccionadas = request.GET.getlist('col')
        if not cols_seleccionadas:
            cols_seleccionadas = ['id', 'username', 'apellido', 'email', 'rol', 'estado']
            
        query = request.GET.get('q', '')
        rol = request.GET.get('rol', '')
        usuarios = Usuario.objects.all()
        if query:
            usuarios = usuarios.filter(Q(username__icontains=query) | Q(email__icontains=query))
        if rol:
            usuarios = usuarios.filter(rol=rol)
        mapeo = {
            'id': {'label': 'ID', 'attr': 'id'},
            'username': {'label': 'Username', 'attr': 'username'},
            'apellido': {'label': 'Apellido', 'attr': 'apellido'},
            'email': {'label': 'Email', 'attr': 'email'},
            'rol': {'label': 'Rol', 'attr': 'rol'},
            'estado': {'label': 'Estado', 'attr': None}
        }

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Usuarios'
        header_fill = PatternFill(start_color="0d1b2a", end_color="0d1b2a", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        alignment = Alignment(horizontal="center", vertical="center")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                        top=Side(style='thin'), bottom=Side(style='thin'))
        
        for col_idx, col_key in enumerate(cols_seleccionadas, 1):
            label = mapeo[col_key]['label']
            cell = sheet.cell(row=2, column=col_idx, value=label)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = alignment
            cell.border = border

        for row_idx, u in enumerate(usuarios, 3):
            for col_idx, col_key in enumerate(cols_seleccionadas, 1):
                if col_key == 'estado':
                    val = 'Activo' if u.activo else 'Pendiente'
                elif col_key == 'rol':
                    val = str(u.rol)
                else:
                    val = getattr(u, mapeo[col_key]['attr'])
                
                cell = sheet.cell(row=row_idx, column=col_idx, value=val)
                cell.alignment = alignment
                cell.border = border
        
        img = Image("/home/shaggylinuxero/flowmatic_admin/static/img/logo.png")
        sheet.row_dimensions[1].height = 100
        img.height = 100
        img.width = 350
        sheet.add_image(img, 'A1')
        for col in sheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except: pass
            sheet.column_dimensions[column].width = max_length + 2
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="usuarios_reporte.xlsx"'
        workbook.save(response)
        return response
    except Exception:
        return redirect('panel_admin')

def registro_candidato(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        clave = request.POST.get('clave', '')
        telefono = request.POST.get('telefono', '').strip() or None

        if not email or not username or not apellido or not clave:
            return render(request, 'registro-candidato.html', {
                'error_campos': True,
            })
        if len(clave) < 8:
            return render(request, 'registro-candidato.html', {
                'error_clave_corta': True,
            })

        try:
            if Usuario.objects.filter(email=email).exists():
                return render(request, 'registro-candidato.html', {
                    'error_duplicado': True,
                })
        except Exception:
            return render(request, 'registro-candidato.html', {
                'error_duplicado': True,
            })

        token = str(uuid.uuid4())
        try:
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
        try:
            send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [email], html_message=mensaje, fail_silently=False)
        except smtplib.SMTPException:
            pass

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
