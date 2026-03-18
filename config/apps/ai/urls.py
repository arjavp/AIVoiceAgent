from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VoiceWorkflowViewSet,
    DocumentUploadView, DocumentListView,
    TicketListView, TicketDetailView,
    DraftEmailListView, DraftEmailDetailView,
)

router = DefaultRouter()
router.register(r'workflows', VoiceWorkflowViewSet, basename='workflow')

urlpatterns = [
    path('', include(router.urls)),
    # Knowledge base
    path('upload/', DocumentUploadView.as_view(), name='document_upload'),
    path('documents/', DocumentListView.as_view(), name='document_list'),
    # Tickets
    path('tickets/', TicketListView.as_view(), name='ticket_list'),
    path('tickets/<uuid:ticket_id>/', TicketDetailView.as_view(), name='ticket_detail'),
    # Draft emails
    path('emails/', DraftEmailListView.as_view(), name='draft_email_list'),
    path('emails/<uuid:email_id>/', DraftEmailDetailView.as_view(), name='draft_email_detail'),
]