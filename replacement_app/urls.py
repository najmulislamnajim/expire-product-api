from django.urls import path 
import replacement_app.views as replacement_views

urlpatterns = [
    path('available_list',replacement_views.AvailableReplacementListView2.as_view(), name='available_list'),
    path('create', replacement_views.ReplacementListCreateAPIView.as_view(), name="replacement_create"),
    path('approve', replacement_views.ReplacementApproveView.as_view(), name="replacement approve"),
    path('approval_list', replacement_views.ReplacementApprovalListView.as_view(), name="replacement_approval_list"),
    path('request/list', replacement_views.ReplacementOrderRequestList.as_view(), name='replacement_request_list'),
    path('assign_delivery_da', replacement_views.AssignDeliveryDA.as_view(), name='assign_delivery_da'),
    path('delivery_pending_list', replacement_views.ReplacementDeliveryPendingList.as_view(), name='delivery_pending_list'),
    path('delivered_list', replacement_views.ReplacementDeliveredList.as_view(), name='delivered_list'),
    path('delivery/<str:invoice_no>', replacement_views.ReplacementDelivery.as_view(), name='replacement_delivery'),
]
