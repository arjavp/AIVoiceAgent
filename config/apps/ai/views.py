from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
import PyPDF2

from .models import VoiceWorkflow, KnowledgeBaseDocument, Ticket, DraftEmail
from .services.rag_service import get_rag_service


# ── Serializers ──

class VoiceWorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceWorkflow
        fields = ['id', 'name', 'graph_schema', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
        
class KnowledgeBaseDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBaseDocument
        fields = ['id', 'filename', 'file_type', 'file_size', 'chunk_count', 'uploaded_at', 'description']
        read_only_fields = ['id', 'uploaded_at', 'chunk_count']

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['id', 'title', 'description', 'status', 'priority', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class DraftEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DraftEmail
        fields = ['id', 'subject', 'body', 'recipient', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at']


# ── ViewSets / Views ──

class VoiceWorkflowViewSet(viewsets.ModelViewSet):
    serializer_class = VoiceWorkflowSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return VoiceWorkflow.objects.filter(user=self.request.user)
        
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DocumentUploadView(APIView):
    permission_classes = [permissions.AllowAny]  # Adjust as needed (e.g. IsAuthenticated)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded. Please send a 'file' parameter."}, status=status.HTTP_400_BAD_REQUEST)
        
        description = request.data.get('description', '')
        user = request.user if request.user.is_authenticated else None
            
        try:
            text_content = ""
            file_type = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else 'txt'
            
            # Check if it's a PDF
            if file_type == 'pdf':
                # Reset file pointer to beginning
                file_obj.seek(0)
                pdf_reader = PyPDF2.PdfReader(file_obj)
                text_content = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    extracted = page.extract_text()
                    if extracted:
                        text_content += extracted + "\n"
                        
                if not text_content.strip():
                    return Response({"error": "Could not extract readable text from the PDF. The file might be image-based or corrupted."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Fallback for plain text files
                file_obj.seek(0)
                try:
                    text_content = file_obj.read().decode('utf-8')
                except UnicodeDecodeError:
                    return Response({"error": "File encoding not supported. Please upload a UTF-8 encoded text file or PDF."}, status=status.HTTP_400_BAD_REQUEST)

            if not text_content.strip():
                return Response({"error": "Could not extract readable text from the file."}, status=status.HTTP_400_BAD_REQUEST)

            # Ingest into PGVector via LangChain with improved chunking
            # Use singleton to avoid reloading embeddings model on every request
            rag_service = get_rag_service()
            metadata = {
                'filename': file_obj.name,
                'file_type': file_type,
                'source': file_obj.name
            }
            chunk_count = rag_service.load_documents(text_content, metadata=metadata)
            
            # Save document record
            doc_record = KnowledgeBaseDocument.objects.create(
                user=user,
                filename=file_obj.name,
                file_type=file_type,
                file_size=file_obj.size,
                chunk_count=chunk_count,
                description=description
            )
            
            return Response({
                "message": f"Successfully uploaded {file_obj.name} and inserted {chunk_count} chunks into the Knowledge Base! The Voice Agent can now answer questions about it.",
                "document": KnowledgeBaseDocumentSerializer(doc_record).data
            }, status=status.HTTP_201_CREATED)
            
        except PyPDF2.errors.PdfReadError as e:
            return Response({"error": f"Invalid PDF file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to process document: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentListView(APIView):
    """List all uploaded knowledge base documents."""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, *args, **kwargs):
        documents = KnowledgeBaseDocument.objects.all()
        serializer = KnowledgeBaseDocumentSerializer(documents, many=True)
        return Response({
            "count": documents.count(),
            "documents": serializer.data
        }, status=status.HTTP_200_OK)


class TicketListView(APIView):
    """List all tickets created by the voice agent."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        tickets = Ticket.objects.all()
        serializer = TicketSerializer(tickets, many=True)
        return Response({
            "count": tickets.count(),
            "tickets": serializer.data
        }, status=status.HTTP_200_OK)


class TicketDetailView(APIView):
    """Get or update a single ticket."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, ticket_id, *args, **kwargs):
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, ticket_id, *args, **kwargs):
        """Update ticket status or priority."""
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            new_status = request.data.get('status')
            new_priority = request.data.get('priority')
            if new_status and new_status in dict(Ticket.STATUS_CHOICES):
                ticket.status = new_status
            if new_priority and new_priority in dict(Ticket.PRIORITY_CHOICES):
                ticket.priority = new_priority
            ticket.save()
            return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)


class DraftEmailListView(APIView):
    """List all draft emails created by the voice agent."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        drafts = DraftEmail.objects.all()
        serializer = DraftEmailSerializer(drafts, many=True)
        return Response({
            "count": drafts.count(),
            "drafts": serializer.data
        }, status=status.HTTP_200_OK)


class DraftEmailDetailView(APIView):
    """Get a single draft email."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, email_id, *args, **kwargs):
        try:
            draft = DraftEmail.objects.get(id=email_id)
            return Response(DraftEmailSerializer(draft).data, status=status.HTTP_200_OK)
        except DraftEmail.DoesNotExist:
            return Response({"error": "Draft email not found"}, status=status.HTTP_404_NOT_FOUND)