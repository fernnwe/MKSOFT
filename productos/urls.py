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
    path("categorias/<int:pk>/eliminar/", views.CategoriaDeleteView.as_view(), name="categoria_eliminar"),
    path("pdf/productos/", views.productos_pdf, name="productos_pdf"),
    path("<int:producto_pk>/recetas/", views.RecetaListView.as_view(), name="recetas"),
    path("<int:producto_pk>/recetas/crear/", views.RecetaCreateView.as_view(), name="receta_crear"),
    path("<int:producto_pk>/recetas/<int:pk>/editar/", views.RecetaUpdateView.as_view(), name="receta_editar"),
    path("<int:producto_pk>/recetas/<int:pk>/eliminar/", views.RecetaDeleteView.as_view(), name="receta_eliminar"),
]
