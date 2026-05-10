from django.urls import path
from . import views

app_name = "respaldos"

urlpatterns = [
    path("", views.BackupListView.as_view(), name="list"),
    path("crear/", views.crear_respaldo, name="crear"),
    path("restaurar/<uuid:backup_id>/", views.restaurar_respaldo, name="restaurar"),
    path("descargar/<uuid:backup_id>/", views.descargar_respaldo, name="descargar"),
    path("eliminar/<uuid:backup_id>/", views.eliminar_respaldo, name="eliminar"),
]
