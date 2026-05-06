from django.urls import path
from . import views

app_name = "productos"

urlpatterns = [
    path("", views.ProductoListView.as_view(), name="list"),
    path("crear/", views.ProductoCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.ProductoUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.ProductoDeleteView.as_view(), name="eliminar"),
    path("categorias/", views.CategoriaListView.as_view(), name="categorias"),
    path("categorias/crear/", views.CategoriaCreateView.as_view(), name="categoria_crear"),
]
