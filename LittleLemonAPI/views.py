from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth.models import Group, User
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .permissions import IsManager, IsDeliveryCrew, IsManagerOrReadOnly
from .models import MenuItem, Category, Cart, Order, OrderItem
from .serializers import (
    MenuItemSerializer, CategorySerializer, CartSerializer,
    CartAddSerializer, OrderSerializer, OrderItemSerializer, OrderStatusUpdateSerializer
)

class ThrottleUserRate(UserRateThrottle):
    rate = '5/minute'

# User and Group Management Views
@api_view(['POST'])
def add_to_group(request, group_name):
    if not request.user.groups.filter(name='Manager').exists() and not request.user.is_superuser:
        return Response({"message": "Forbidden. Only managers can perform this action."}, status=status.HTTP_403_FORBIDDEN)
    
    if 'username' not in request.data:
        return Response({"message": "Bad Request. Username is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username=request.data['username'])
        group = Group.objects.get(name=group_name)
        user.groups.add(group)
        return Response({"message": f"{user.username} added to {group_name} group"}, status=status.HTTP_201_CREATED)
    except User.DoesNotExist:
        return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    except Group.DoesNotExist:
        return Response({"message": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
def remove_from_group(request, group_name, userId):
    if not request.user.groups.filter(name='Manager').exists() and not request.user.is_superuser:
        return Response({"message": "Forbidden. Only managers can perform this action."}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(pk=userId)
        group = Group.objects.get(name=group_name)
        user.groups.remove(group)
        return Response({"message": f"{user.username} removed from {group_name} group"}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    except Group.DoesNotExist:
        return Response({"message": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

class GroupListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class = MenuItemSerializer # This is not used, just a placeholder

    def list(self, request, *args, **kwargs):
        group_name = self.kwargs['group_name']
        try:
            group = Group.objects.get(name=group_name)
            users = group.user_set.all()
            user_list = [{"username": user.username} for user in users]
            return Response(user_list, status=status.HTTP_200_OK)
        except Group.DoesNotExist:
            return Response({"message": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

# Menu Item Views
class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    throttle_classes = [ThrottleUserRate]
    ordering_fields = ['price', 'title']
    search_fields = ['title', 'category__title']
    
    def get_permissions(self):
        # Allow any user to GET (read-only) menu items
        if self.request.method == 'GET':
            self.permission_classes = [] # This effectively sets it to AllowAny
        # Only managers can POST (create) new menu items
        else:
            self.permission_classes = [IsAuthenticated, IsManager]
        return super().get_permissions()

class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    throttle_classes = [ThrottleUserRate]

    def get_permissions(self):
        # Allow any user to GET (read-only) a single menu item
        if self.request.method == 'GET':
            self.permission_classes = [] # This effectively sets it to AllowAny
        # Only managers can PUT/PATCH/DELETE
        else:
            self.permission_classes = [IsAuthenticated, IsManager]
        return super().get_permissions()

# Cart Management Views
class CartView(generics.ListCreateAPIView, generics.DestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CartAddSerializer
        return CartSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Item added to cart successfully"}, status=status.HTTP_201_CREATED)
    
    def delete(self, request, *args, **kwargs):
        with transaction.atomic():
            cart_items = self.get_queryset()
            if not cart_items.exists():
                return Response({"message": "Cart is already empty."}, status=status.HTTP_404_NOT_FOUND)
            cart_items.delete()
        return Response({"message": "Cart cleared successfully."}, status=status.HTTP_200_OK)

# Order Management Views
class OrderView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    throttle_classes = [ThrottleUserRate]
    filterset_fields = ['status']
    ordering_fields = ['total', 'date']

    def get_permissions(self):
        if self.request.method == 'GET' and self.request.user.groups.filter(name='Manager').exists():
            self.permission_classes = [IsAuthenticated, IsManager]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        elif user.groups.filter(name='Delivery Crew').exists():
            return Order.objects.filter(delivery_crew=user)
        return Order.objects.filter(user=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = self.request.user
        cart_items = Cart.objects.filter(user=user)
        if not cart_items.exists():
            return Response({"message": "Cart is empty, cannot place an order."}, status=status.HTTP_400_BAD_REQUEST)
        
        total = sum(item.price for item in cart_items)
        
        order = Order.objects.create(user=user, total=total)
        
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                menuitem=item.menuitem,
                quantity=item.quantity,
                unit_price=item.unit_price,
                price=item.price
            )
        
        cart_items.delete()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    throttle_classes = [ThrottleUserRate]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        elif user.groups.filter(name='Delivery Crew').exists():
            return Order.objects.filter(delivery_crew=user)
        return Order.objects.filter(user=user)
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            if self.request.user.groups.filter(name='Manager').exists():
                self.permission_classes = [IsAuthenticated, IsManager]
            elif self.request.user.groups.filter(name='Delivery Crew').exists():
                self.permission_classes = [IsAuthenticated, IsDeliveryCrew]
            else:
                self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = self.request.user

        # Manager can update delivery crew and status
        if user.groups.filter(name='Manager').exists():
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Delivery crew can only update status
        elif user.groups.filter(name='Delivery Crew').exists():
            if 'status' not in request.data:
                return Response({"message": "You can only update the status field."}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = OrderStatusUpdateSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Customers cannot update orders
        return Response({"message": "Forbidden. You cannot update this order."}, status=status.HTTP_403_FORBIDDEN)
