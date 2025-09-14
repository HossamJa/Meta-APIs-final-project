from django.urls import path
from . import views

urlpatterns = [
    # Menu Item Endpoints
    path('menu-items/', views.MenuItemsView.as_view()),
    path('menu-items/<int:pk>', views.SingleMenuItemView.as_view()),
    
    # User Group Management Endpoints
    path('groups/<str:group_name>/users/', views.GroupListView.as_view()),
    path('groups/<str:group_name>/users/add', views.add_to_group),
    path('groups/<str:group_name>/users/<int:userId>', views.remove_from_group),

    # Cart Management Endpoints
    path('cart/menu-items/', views.CartView.as_view()),
    
    # Order Management Endpoints
    path('orders/', views.OrderView.as_view()),
    path('orders/<int:pk>', views.OrderDetailView.as_view()),
]