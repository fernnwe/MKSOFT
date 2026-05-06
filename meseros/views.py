from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Mesero

User = get_user_model()


class MeseroListView(LoginRequiredMixin, ListView):
    model = Mesero
    template_name = "meseros/list.html"
    context_object_name = "meseros"


class MeseroCreateView(LoginRequiredMixin, CreateView):
    model = Mesero
    template_name = "meseros/form.html"
    fields = ["usuario", "activo"]
    success_url = reverse_lazy("meseros:list")

    def form_valid(self, form):
        messages.success(self.request, "Mesero registrado exitosamente")
        return super().form_valid(form)


class MeseroUpdateView(LoginRequiredMixin, UpdateView):
    model = Mesero
    template_name = "meseros/form.html"
    fields = ["usuario", "activo"]
    success_url = reverse_lazy("meseros:list")

    def form_valid(self, form):
        messages.success(self.request, "Mesero actualizado exitosamente")
        return super().form_valid(form)


class MeseroDeleteView(LoginRequiredMixin, DeleteView):
    model = Mesero
    success_url = reverse_lazy("meseros:list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Mesero eliminado")
        return super().delete(request, *args, **kwargs)
