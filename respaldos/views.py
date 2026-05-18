import os
import json
import uuid
import hashlib
import decimal
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView
from django.core.management import call_command
from django.conf import settings
from django.db import connection, transaction
from io import StringIO

from .models import DatabaseBackup, TENANT_APPS


class BackupListView(LoginRequiredMixin, ListView):
    model = DatabaseBackup
    template_name = "respaldos/list.html"
    context_object_name = "respaldos"
    paginate_by = 20

    def get_queryset(self):
        qs = DatabaseBackup.objects.select_related("creado_por", "restaurado_por", "cliente")
        if not self.request.user.is_superuser:
            cliente = getattr(self.request.user, "cliente", None)
            if cliente:
                qs = qs.filter(cliente=cliente)
            else:
                qs = qs.none()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ultimo_respaldo"] = self.get_queryset().filter(estado=DatabaseBackup.Estado.EXITOSO).first()
        return context


@login_required
def crear_respaldo(request):
    cliente = getattr(request.user, "cliente", None)
    if not cliente and not request.user.is_superuser:
        messages.error(request, "No tienes acceso a esta funcion")
        return redirect("core:dashboard")

    context = {"cliente": cliente, "is_superadmin": request.user.is_superuser}

    if request.user.is_superuser:
        from core.models import Cliente
        context["clientes"] = Cliente.objects.all().order_by("nombre_negocio")

        selected_pk = request.GET.get("cliente")
        if selected_pk:
            context["selected_cliente"] = Cliente.objects.filter(pk=selected_pk).first()

    if request.method == "POST":
        backup_type = request.POST.get("tipo", "completo")

        if request.user.is_superuser:
            from core.models import Cliente
            if backup_type == "completo":
                backup = DatabaseBackup.objects.create(
                    nombre=f"Respaldo_Completo_{timezone.now():%Y%m%d_%H%M%S}",
                    creado_por=request.user,
                    tipo=DatabaseBackup.Tipo.COMPLETO,
                    estado=DatabaseBackup.Estado.PENDIENTE,
                )
            elif backup_type == "tenant":
                cliente_id = request.POST.get("cliente_id")
                if not cliente_id:
                    messages.error(request, "Selecciona un restaurante")
                    return render(request, "respaldos/confirm_crear.html", context)
                cliente = Cliente.objects.filter(pk=cliente_id).first()
                if not cliente:
                    messages.error(request, "Restaurante no encontrado")
                    return render(request, "respaldos/confirm_crear.html", context)
                backup = DatabaseBackup.objects.create(
                    nombre=f"Respaldo_{cliente.nombre_negocio}_{timezone.now():%Y%m%d_%H%M%S}",
                    creado_por=request.user,
                    cliente=cliente,
                    tipo=DatabaseBackup.Tipo.TENANT,
                    estado=DatabaseBackup.Estado.PENDIENTE,
                )
            else:
                messages.error(request, "Tipo de respaldo no valido")
                return render(request, "respaldos/confirm_crear.html", context)
        else:
            backup = DatabaseBackup.objects.create(
                nombre=f"Respaldo_{cliente.nombre_negocio}_{timezone.now():%Y%m%d_%H%M%S}",
                creado_por=request.user,
                cliente=cliente,
                tipo=DatabaseBackup.Tipo.TENANT,
                estado=DatabaseBackup.Estado.PENDIENTE,
            )

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]

            if backup.tipo == DatabaseBackup.Tipo.COMPLETO:
                filename = f"backup_completo_{timestamp}_{unique_id}.json"
                backup_path = os.path.join(settings.MEDIA_ROOT, "respaldos", filename)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)

                with open(backup_path, "w", encoding="utf-8") as f:
                    call_command("dumpdata", stdout=f, format="json", natural_foreign=True, exclude=["contenttypes", "auth.permission", "sessions"])
            else:
                filename = f"backup_tenant_{timestamp}_{unique_id}.json"
                backup_path = os.path.join(settings.MEDIA_ROOT, "respaldos", str(cliente.pk), filename)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)

                data = []
                for app_model in TENANT_APPS:
                    app_label, model_name = app_model.split(".")
                    model = __import__(f"{app_label}.models", fromlist=[model_name]).__dict__[model_name]

                    if hasattr(model, 'cliente'):
                        qs = model.objects.filter(cliente=cliente)
                    else:
                        filter_lookups = {
                            "Receta": "producto__cliente",
                            "CajaMovimiento": "caja__cliente",
                            "Inventario": "ingrediente__cliente",
                            "MovimientoInventario": "inventario__ingrediente__cliente",
                            "CompraItem": "compra__cliente",
                            "ComandaItem": "comanda__cliente",
                        }
                        lookup = filter_lookups.get(model_name)
                        if lookup:
                            qs = model.objects.filter(**{lookup: cliente})
                        else:
                            continue

                    for obj in qs:
                        item = {
                            "model": f"{app_label}.{model_name}",
                            "pk": str(obj.pk) if not isinstance(obj.pk, (int, str)) else obj.pk,
                            "fields": {},
                        }
                        for field in obj._meta.fields:
                            if field.name == "id" or field.name == "cliente":
                                continue
                            if field.is_relation:
                                value = getattr(obj, field.attname)
                            else:
                                value = getattr(obj, field.name)
                            if isinstance(value, decimal.Decimal):
                                value = float(value)
                            elif hasattr(value, "isoformat"):
                                value = value.isoformat()
                            elif not isinstance(value, (str, int, float, bool, type(None))):
                                value = str(value)
                            item["fields"][field.name] = value
                        data.append(item)
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            rel_path = os.path.relpath(backup_path, settings.MEDIA_ROOT).replace("\\", "/")
            with open(backup_path, "rb") as src:
                backup.archivo.save(rel_path, src, save=False)
            backup.estado = DatabaseBackup.Estado.EXITOSO
            backup.calcular_tamaño()

            try:
                with open(backup_path, "rb") as f:
                    backup.hash_md5 = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass

            backup.save()
            msg = "Respaldo completo creado" if backup.tipo == DatabaseBackup.Tipo.COMPLETO else f"Respaldo de {cliente.nombre_negocio} creado"
            messages.success(request, f"{msg} ({backup.tamaño_mb:.2f} MB)")

        except Exception as e:
            backup.estado = DatabaseBackup.Estado.FALLIDO
            backup.notas = f"Error: {str(e)}"
            backup.save()
            messages.error(request, f"Error al crear el respaldo: {str(e)}")

        return redirect("respaldos:list")

    return render(request, "respaldos/confirm_crear.html", context)


@login_required
def restaurar_respaldo(request, backup_id):
    backup = get_object_or_404(DatabaseBackup, pk=backup_id)

    if not request.user.is_superuser:
        cliente = getattr(request.user, "cliente", None)
        if not cliente or backup.cliente != cliente:
            messages.error(request, "No tienes acceso a este respaldo")
            return redirect("respaldos:list")

    if request.method == "POST":
        if not backup.archivo or not os.path.exists(backup.archivo.path):
            messages.error(request, "El archivo de respaldo no existe")
            return redirect("respaldos:list")

        backup.estado = DatabaseBackup.Estado.RESTAURANDO
        backup.fecha_restauracion = timezone.now()
        backup.restaurado_por = request.user
        backup.save(update_fields=["estado", "fecha_restauracion", "restaurado_por"])

        try:
            if backup.tipo == DatabaseBackup.Tipo.COMPLETO:
                from django.db import connections
                for conn in connections.all():
                    conn.close()

                import shutil
                db_path = str(settings.DATABASES["default"]["NAME"])
                if connection.vendor == "sqlite":
                    shutil.copy2(backup.archivo.path, db_path)
                    for ext in ["-wal", "-shm"]:
                        src_path = backup.archivo.path + ext
                        dst_path = db_path + ext
                        if os.path.exists(src_path):
                            shutil.copy2(src_path, dst_path)
                        elif os.path.exists(dst_path):
                            os.remove(dst_path)
                else:
                    with open(backup.archivo.path, "r") as f:
                        call_command("loaddata", f.name)
            else:
                with transaction.atomic():
                    cliente = backup.cliente
                    from facturacion.models import Factura, CajaApertura, CajaMovimiento
                    from comandas.models import Comanda, ComandaItem
                    from mesas.models import Mesa
                    from productos.models import Producto, Categoria
                    from meseros.models import Mesero
                    from inventario.models import Ingrediente, Compra, CompraItem, CuentaPorPagar, Inventario, MovimientoInventario, Receta

                    delete_order = [
                        ComandaItem, CajaMovimiento, Factura, Comanda, Mesa,
                        Mesero, CuentaPorPagar, MovimientoInventario,
                        CompraItem, Compra, Inventario, Receta, Ingrediente,
                        Producto, Categoria, CajaApertura,
                    ]
                    for model in delete_order:
                        if hasattr(model, 'cliente'):
                            model.objects.filter(cliente=cliente).delete()
                        else:
                            delete_lookups = {
                                "ComandaItem": "comanda__cliente",
                                "CajaMovimiento": "caja__cliente",
                                "Receta": "producto__cliente",
                                "MovimientoInventario": "inventario__ingrediente__cliente",
                                "CompraItem": "compra__cliente",
                                "Inventario": "ingrediente__cliente",
                            }
                            lookup = delete_lookups.get(model.__name__)
                            if lookup:
                                model.objects.filter(**{lookup: cliente}).delete()

                    with open(backup.archivo.path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    grouped = {}
                    for item in data:
                        model_key = item["model"]
                        grouped.setdefault(model_key, []).append(item)

                    restore_order = [
                        "mesas.Mesa",
                        "productos.Categoria",
                        "inventario.Ingrediente",
                        "inventario.Inventario",
                        "meseros.Mesero",
                        "productos.Producto",
                        "inventario.Receta",
                        "comandas.Comanda",
                        "inventario.Compra",
                        "comandas.ComandaItem",
                        "inventario.CompraItem",
                        "inventario.MovimientoInventario",
                        "facturacion.Factura",
                        "facturacion.CajaApertura",
                        "facturacion.CajaMovimiento",
                        "inventario.CuentaPorPagar",
                    ]

                    for model_key in restore_order:
                        items = grouped.get(model_key, [])
                        if not items:
                            continue
                        app_label, model_name = model_key.split(".")
                        model = __import__(f"{app_label}.models", fromlist=[model_name]).__dict__[model_name]
                        for item in items:
                            pk = item["pk"]
                            fields = dict(item["fields"])
                            fk_fields = [f.name for f in model._meta.fields if f.is_relation and f.name != "cliente"]
                            for fk_name in fk_fields:
                                if fk_name in fields and fields[fk_name] is not None:
                                    fk_model = model._meta.get_field(fk_name).related_model
                                    if fk_model._meta.app_label != app_label:
                                        try:
                                            fields[fk_name] = fk_model.objects.get(pk=fields[fk_name])
                                        except fk_model.DoesNotExist:
                                            fields[fk_name] = None
                            fields["cliente"] = cliente
                            model.objects.create(pk=pk, **fields)

            backup.estado = DatabaseBackup.Estado.RESTAURADO
            backup.save(update_fields=["estado"])
            messages.success(request, "Respaldo restaurado exitosamente")

        except Exception as e:
            backup.estado = DatabaseBackup.Estado.FALLIDO
            backup.notas = f"Error al restaurar: {str(e)}"
            backup.save(update_fields=["estado", "notas"])
            messages.error(request, f"Error al restaurar: {str(e)}")

        return redirect("respaldos:list")

    return render(request, "respaldos/confirm_restaurar.html", {"backup": backup})


@login_required
def descargar_respaldo(request, backup_id):
    backup = get_object_or_404(DatabaseBackup, pk=backup_id)

    if not request.user.is_superuser:
        cliente = getattr(request.user, "cliente", None)
        if not cliente or backup.cliente != cliente:
            messages.error(request, "No tienes acceso a este respaldo")
            return redirect("respaldos:list")

    if not backup.archivo or not os.path.exists(backup.archivo.path):
        messages.error(request, "El archivo de respaldo no existe")
        return redirect("respaldos:list")

    response = FileResponse(
        open(backup.archivo.path, "rb"),
        content_type="application/octet-stream",
    )
    ext = ".json"
    response["Content-Disposition"] = f'attachment; filename="{backup.nombre}{ext}"'
    return response


@login_required
def eliminar_respaldo(request, backup_id):
    backup = get_object_or_404(DatabaseBackup, pk=backup_id)

    if not request.user.is_superuser:
        cliente = getattr(request.user, "cliente", None)
        if not cliente or backup.cliente != cliente:
            messages.error(request, "No tienes acceso a este respaldo")
            return redirect("respaldos:list")

    if request.method == "POST":
        try:
            backup.eliminar_archivo()
            backup.delete()
            messages.success(request, "Respaldo eliminado")
        except Exception as e:
            messages.error(request, f"Error al eliminar: {str(e)}")
        return redirect("respaldos:list")

    return render(request, "respaldos/confirm_eliminar.html", {"backup": backup})
