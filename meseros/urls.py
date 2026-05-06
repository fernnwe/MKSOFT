from django.urls import path
from . import views

app_name = "meseros"

urlpatterns = [
    path("", views.MeseroListView.as_view(), name="list"),
    path("crear/", views.MeseroCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.MeseroUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.MeseroDeleteView.as_view(), name="eliminar"),
]
