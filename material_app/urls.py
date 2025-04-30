from django.urls import path
from . import views as material_views

urlpatterns = [
    path('list', material_views.RplMaterialListView.as_view(), name='material_list'),
]