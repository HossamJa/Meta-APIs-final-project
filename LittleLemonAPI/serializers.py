from rest_framework import serializers
from django.contrib.auth.models import User
from .models import MenuItem, Category, Cart, Order, OrderItem

# Serializer for the Category model
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'title']

# Serializer for the MenuItem model
class MenuItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'category', 'category_id']

# Serializer for the Cart model
class CartSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField() # Displays the username
    menuitem = MenuItemSerializer(read_only=True)
    menuitem_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Cart
        fields = ['user', 'menuitem', 'menuitem_id', 'quantity', 'unit_price', 'price']
        read_only_fields = ['user', 'unit_price', 'price']

# Serializer for adding an item to the cart
class CartAddSerializer(serializers.ModelSerializer):
    menuitem_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Cart
        fields = ['menuitem_id', 'quantity']
        extra_kwargs = {
            'quantity': {'min_value': 1}
        }

    def create(self, validated_data):
        user = self.context['request'].user
        menuitem_id = validated_data['menuitem_id']
        quantity = validated_data['quantity']

        # Check if the menu item exists
        try:
            menuitem = MenuItem.objects.get(pk=menuitem_id)
        except MenuItem.DoesNotExist:
            raise serializers.ValidationError({"detail": "Menu item does not exist."})
        
        # Calculate unit price and total price
        unit_price = menuitem.price
        price = unit_price * quantity
        
        # Create or update the cart item
        cart_item, created = Cart.objects.get_or_create(
            user=user,
            menuitem=menuitem,
            defaults={'quantity': quantity, 'unit_price': unit_price, 'price': price}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.price += price
            cart_item.save()
            
        return cart_item

# Serializer for the Order model
class OrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    delivery_crew = serializers.StringRelatedField()
    order_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'status', 'total', 'date', 'order_items']
        read_only_fields = ['user', 'total']

    def get_order_items(self, obj):
        order_items = OrderItem.objects.filter(order=obj)
        return OrderItemSerializer(order_items, many=True).data

# Serializer for the OrderItem model
class OrderItemSerializer(serializers.ModelSerializer):
    menuitem = MenuItemSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'menuitem', 'quantity', 'unit_price', 'price']
        read_only_fields = ['order', 'unit_price', 'price']

# Serializer for updating the order status
class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']
