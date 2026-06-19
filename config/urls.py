from django.contrib import admin
from django.urls import path
from admin_panel import views
# esto es una prueba
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-panel/', views.panel_admin, name='panel_admin'),
    path('admin-panel/crear-rrhh/', views.crear_rrhh, name='crear_rrhh'),
    path('admin-panel/eliminar/<int:usuario_id>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('admin-panel/editar/', views.editar_usuario, name='editar_usuario'),
    path('admin-panel/exportar/', views.exportar_excel, name='exportar_excel'),
]
