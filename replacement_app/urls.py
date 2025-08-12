from django.urls import path 
import replacement_app.views as replacement_views

urlpatterns = [
    path('available_list',replacement_views.AvailableReplacementListView.as_view(), name='available_list'),
]
