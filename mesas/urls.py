from django.urls import path
from . import views

app_name = "mesas"

urlpatterns = [
    path("", views.MesaListView.as_view(), name="list"),
    path("plano/", views.MesaPlanoView.as_view(), name="plano"),
    path("crear/", views.MesaCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.MesaUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.MesaDeleteView.as_view(), name="eliminar"),
    path("<int:pk>/estado/<str:estado>/", views.cambiar_estado_mesa, name="cambiar_estado"),
]
