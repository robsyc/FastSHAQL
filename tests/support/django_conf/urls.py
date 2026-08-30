"""Mutable URLconf — tests assign urlpatterns before each request."""

from django.urls import URLPattern

urlpatterns: list[URLPattern] = []
