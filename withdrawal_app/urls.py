from django.urls import path 
from .import views as withdrawal_views

urlpatterns = [
    path('request', withdrawal_views.WithdrawalRequestView.as_view(), name='withdrawal_request'),
    path('list', withdrawal_views.WithdrawalListView.as_view(), name='withdrawal_list'),
]