from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class ConfigRestaurante(models.Model):
    nombre = models.CharField(max_length=200, default="Mi Restaurante")
    rfc = models.CharField(max_length=13, default="XAXX010101000", blank=True)
    direccion = models.TextField(default="Calle Principal #123", blank=True)
    telefono = models.CharField(max_length=20, default="+52 55 1234 5678", blank=True)
    email = models.EmailField(default="", blank=True)
    simbolo_moneda = models.CharField(max_length=5, default="C$")
    tasa_impuesto = models.FloatField(default=0.16, help_text="Ej: 0.16 para 16%")
    logo = models.ImageField(upload_to="restaurante/", blank=True, null=True)
    dias_credito_proveedor = models.PositiveIntegerField(default=30, help_text="Dias para pagar a proveedores (cuentas por pagar)")
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracion del Restaurante"
        verbose_name_plural = "Configuracion del Restaurante"

    def __str__(self):
        return self.nombre

    @classmethod
    def get_config(cls):
        config = cls.objects.first()
        if not config:
            from django.conf import settings
            config = cls.objects.create(
                nombre=settings.RESTAURANT_NAME,
                rfc=settings.RESTAURANT_RFC,
                direccion=settings.RESTAURANT_ADDRESS,
                telefono=settings.RESTAURANT_PHONE,
                simbolo_moneda=settings.CURRENCY_SYMBOL,
                tasa_impuesto=settings.TAX_RATE,
                dias_credito_proveedor=getattr(settings, "DIAS_CREDITO_PROVEEDOR", 30),
            )
        return config


@receiver(post_migrate)
def crear_config_restaurante(sender, **kwargs):
    if sender.name == "core":
        if not ConfigRestaurante.objects.exists():
            from django.conf import settings
            ConfigRestaurante.objects.create(
                nombre=settings.RESTAURANT_NAME,
                rfc=settings.RESTAURANT_RFC,
                direccion=settings.RESTAURANT_ADDRESS,
                telefono=settings.RESTAURANT_PHONE,
                simbolo_moneda=settings.CURRENCY_SYMBOL,
                tasa_impuesto=settings.TAX_RATE,
                dias_credito_proveedor=getattr(settings, "DIAS_CREDITO_PROVEEDOR", 30),
            )


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        MANAGER = "manager", "Gerente"
        WAITER = "waiter", "Mesero"
        CASHIER = "cashier", "Cajero"
        KITCHEN = "kitchen", "Cocina"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WAITER)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="users/", blank=True, null=True)
    is_active_staff = models.BooleanField(default=True)
    visible_password = models.CharField(max_length=255, blank=True, default="", help_text="Contraseña visible solo para administradores")
    custom_permissions = models.JSONField(default=dict, blank=True)

    ROLE_PERMISSIONS = {
        "admin": {
            "can_view_dashboard": True,
            "can_view_mesas": True,
            "can_view_comandas": True,
            "can_create_comandas": True,
            "can_manage_comandas": True,
            "can_view_cocina": True,
            "can_view_productos": True,
            "can_manage_productos": True,
            "can_view_inventario": True,
            "can_manage_inventario": True,
            "can_view_facturacion": True,
            "can_create_facturas": True,
            "can_cancel_facturas": True,
            "can_manage_users": True,
            "can_delete_users": True,
        },
        "manager": {
            "can_view_dashboard": True,
            "can_view_mesas": True,
            "can_view_comandas": True,
            "can_create_comandas": True,
            "can_manage_comandas": True,
            "can_view_cocina": True,
            "can_view_productos": True,
            "can_manage_productos": True,
            "can_view_inventario": True,
            "can_manage_inventario": True,
            "can_view_facturacion": True,
            "can_create_facturas": True,
            "can_cancel_facturas": True,
            "can_manage_users": True,
            "can_delete_users": False,
        },
        "waiter": {
            "can_view_dashboard": True,
            "can_view_mesas": True,
            "can_view_comandas": True,
            "can_create_comandas": True,
            "can_manage_comandas": False,
            "can_view_cocina": False,
            "can_view_productos": False,
            "can_manage_productos": False,
            "can_view_inventario": False,
            "can_manage_inventario": False,
            "can_view_facturacion": False,
            "can_create_facturas": False,
            "can_cancel_facturas": False,
            "can_manage_users": False,
            "can_delete_users": False,
        },
        "cashier": {
            "can_view_dashboard": True,
            "can_view_mesas": True,
            "can_view_comandas": True,
            "can_create_comandas": False,
            "can_manage_comandas": False,
            "can_view_cocina": False,
            "can_view_productos": False,
            "can_manage_productos": False,
            "can_view_inventario": False,
            "can_manage_inventario": False,
            "can_view_facturacion": True,
            "can_create_facturas": True,
            "can_cancel_facturas": False,
            "can_manage_users": False,
            "can_delete_users": False,
        },
        "kitchen": {
            "can_view_dashboard": False,
            "can_view_mesas": False,
            "can_view_comandas": False,
            "can_create_comandas": False,
            "can_manage_comandas": False,
            "can_view_cocina": True,
            "can_view_productos": False,
            "can_manage_productos": False,
            "can_view_inventario": False,
            "can_manage_inventario": False,
            "can_view_facturacion": False,
            "can_create_facturas": False,
            "can_cancel_facturas": False,
            "can_manage_users": False,
            "can_delete_users": False,
        },
    }

    PERMISSION_LABELS = {
        "can_view_dashboard": "Dashboard",
        "can_view_mesas": "Mesas",
        "can_view_comandas": "Ver Comandas",
        "can_create_comandas": "Crear Comandas",
        "can_manage_comandas": "Gestionar Comandas",
        "can_view_cocina": "Cocina",
        "can_view_productos": "Productos",
        "can_manage_productos": "Gestionar Productos",
        "can_view_inventario": "Inventario",
        "can_manage_inventario": "Gestionar Inventario",
        "can_view_facturacion": "Facturacion",
        "can_create_facturas": "Crear Facturas",
        "can_cancel_facturas": "Cancelar Facturas",
        "can_manage_users": "Gestionar Usuarios",
        "can_delete_users": "Eliminar Usuarios",
    }

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name() or self.username}"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role in (self.Role.ADMIN, self.Role.MANAGER)

    @property
    def is_waiter(self):
        return self.role == self.Role.WAITER

    def has_perm(self, perm, obj=None):
        if self.is_superuser:
            return True
        if perm in self.custom_permissions:
            return self.custom_permissions[perm]
        role_perms = self.ROLE_PERMISSIONS.get(self.role, {})
        if perm in role_perms:
            return role_perms[perm]
        return super().has_perm(perm, obj)

    def _get_perm(self, name):
        if not self.is_authenticated:
            return False
        if self.is_superuser:
            return True
        if name in self.custom_permissions:
            return self.custom_permissions[name]
        return self.ROLE_PERMISSIONS.get(self.role, {}).get(name, False)

    def _reset_permissions(self):
        self.custom_permissions = {}
        self.save(update_fields=["custom_permissions"])

    @property
    def can_view_dashboard(self): return self._get_perm("can_view_dashboard")
    @property
    def can_view_mesas(self): return self._get_perm("can_view_mesas")
    @property
    def can_view_comandas(self): return self._get_perm("can_view_comandas")
    @property
    def can_create_comandas(self): return self._get_perm("can_create_comandas")
    @property
    def can_manage_comandas(self): return self._get_perm("can_manage_comandas")
    @property
    def can_view_cocina(self): return self._get_perm("can_view_cocina")
    @property
    def can_view_productos(self): return self._get_perm("can_view_productos")
    @property
    def can_manage_productos(self): return self._get_perm("can_manage_productos")
    @property
    def can_view_inventario(self): return self._get_perm("can_view_inventario")
    @property
    def can_manage_inventario(self): return self._get_perm("can_manage_inventario")
    @property
    def can_view_facturacion(self): return self._get_perm("can_view_facturacion")
    @property
    def can_create_facturas(self): return self._get_perm("can_create_facturas")
    @property
    def can_cancel_facturas(self): return self._get_perm("can_cancel_facturas")
    @property
    def can_manage_users(self): return self._get_perm("can_manage_users")
    @property
    def can_delete_users(self): return self._get_perm("can_delete_users")
