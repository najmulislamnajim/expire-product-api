from django.urls import path 
from .import views as withdrawal_views

urlpatterns = [
    path('list', withdrawal_views.WithdrawalListView.as_view(), name='withdrawal_list'),
    path('request/list', withdrawal_views.WithdrawalRequestListView.as_view(), name='withdrawal_request_list'),
    path('request', withdrawal_views.WithdrawalRequestView.as_view(), name='withdrawal_request'),
    path('request/edit', withdrawal_views.WithdrawalRequestUpdateView.as_view(), name='withdrawal_request_edit'),
    path('request/approve/<str:invoice_no>', withdrawal_views.RequestApproveView.as_view(), name='request_approve'),
    path('assign-da', withdrawal_views.DaAssignView.as_view(), name='da_assign'),
    path('save/<str:invoice_no>',withdrawal_views.WithdrawalSaveView.as_view(), name='withdrawal_save'),
    path('confirm/<str:invoice_no>', withdrawal_views.WithdrawalConfirmationView.as_view(), name='withdrawal_confirmation'),
]