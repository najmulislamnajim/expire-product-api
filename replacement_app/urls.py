from django.urls import path 
import replacement_app.views as replacement_views

urlpatterns = [
    path('available_list',replacement_views.AvailableReplacementListView.as_view(), name='available_list'),
    path('create', replacement_views.ReplacementListCreateAPIView.as_view(), name="replacement_create"),
    path('approve', replacement_views.ReplacementApproveView.as_view(), name="replacement approve")
]
