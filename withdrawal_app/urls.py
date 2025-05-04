from django.urls import path 
from .import views as withdrawal_views

urlpatterns = [
    path('request', withdrawal_views.WithdrawalRequestView.as_view(), name='withdrawal_request'),
    path('list', withdrawal_views.WithdrawalListView.as_view(), name='withdrawal_list'),
    path('request/<str:invoice_no>/approve', withdrawal_views.RequestApproveView.as_view(), name='request_approve'),
    path('<str:invoice_no>/confirm', withdrawal_views.WithdrawalConfirmationView.as_view(), name='withdrawal_confirmation'),
]