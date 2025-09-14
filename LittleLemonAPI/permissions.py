from rest_framework import permissions
from django.contrib.auth.models import Group

class IsManager(permissions.BasePermission):
    """
    Custom permission to only allow managers to access the view.
    """
    def has_permission(self, request, view):
        manager_group = Group.objects.get(name='Manager')
        return request.user and request.user.groups.filter(name='Manager').exists()

class IsDeliveryCrew(permissions.BasePermission):
    """
    Custom permission to only allow delivery crew to access the view.
    """
    def has_permission(self, request, view):
        delivery_group = Group.objects.get(name='Delivery Crew')
        return request.user and request.user.groups.filter(name='Delivery Crew').exists()

class IsManagerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow managers to edit, but others to only read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        manager_group = Group.objects.get(name='Manager')
        return request.user and request.user.groups.filter(name='Manager').exists()
