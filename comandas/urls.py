from django.urls import path
from . import views

app_name = "comandas"

urlpatterns = [
    path("", views.ComandaListView.as_view(), name="list"),
    path("crear/", views.ComandaCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.ComandaDetailView.as_view(), name="detalle"),
    path("<int:pk>/agregar-item/", views.agregar_item, name="agregar_item"),
    path("<int:pk>/enviar-cocina/", views.enviar_cocina, name="enviar_cocina"),
    path("<int:pk>/cerrar/", views.cerrar_comanda, name="cerrar"),
    path("<int:pk>/marcar-lista/", views.marcar_lista, name="marcar_lista"),
    path("<int:pk>/reabrir/", views.reabrir_comanda, name="reabrir"),
    path("<int:pk>/eliminar/", views.eliminar_comanda, name="eliminar"),
    path("item/<int:item_pk>/listo/", views.marcar_listo_item, name="item_listo"),
    path("item/<int:item_pk>/cancelar/", views.cancelar_item, name="item_cancelar"),
    path("cocina/", views.VistaCocina.as_view(), name="cocina"),
]
