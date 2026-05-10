from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model
from core.views import ClienteScopeMixin, PermissionRequiredMixin
from .models import Mesero

User = get_user_model()


class MeseroListView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Mesero
    template_name = "meseros/list.html"
    context_object_name = "meseros"
    permission = "can_manage_users"


class MeseroCreateView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Mesero
    template_name = "meseros/form.html"
    fields = ["usuario", "activo"]
    success_url = reverse_lazy("meseros:list")
    permission = "can_manage_users"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        cliente = self.get_cliente()
        qs = User.objects.filter(role__in=["waiter", "cashier"])
        if cliente:
            qs = qs.filter(cliente=cliente)
        form.fields["usuario"].queryset = qs
        return form

    def form_valid(self, form):
        messages.success(self.request, "Mesero registrado exitosamente")
        return super().form_valid(form)


class MeseroUpdateView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Mesero
    template_name = "meseros/form.html"
    fields = ["usuario", "activo"]
    success_url = reverse_lazy("meseros:list")
    permission = "can_manage_users"

    def get_queryset(self):
        qs = super().get_queryset()
        cliente = self.get_cliente()
        if cliente:
            qs = qs.filter(cliente=cliente)
        return qs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        cliente = self.get_cliente()
        qs = User.objects.filter(role__in=["waiter", "cashier"])
        if cliente:
            qs = qs.filter(cliente=cliente)
        form.fields["usuario"].queryset = qs
        return form

    def form_valid(self, form):
        messages.success(self.request, "Mesero actualizado exitosamente")
        return super().form_valid(form)


class MeseroDeleteView(ClienteScopeMixin, PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Mesero
    success_url = reverse_lazy("meseros:list")
    permission = "can_delete_users"

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Mesero eliminado")
        return super().delete(request, *args, **kwargs)
