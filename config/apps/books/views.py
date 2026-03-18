import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import BookSerializer
from .services import BookService

logger = logging.getLogger(__name__)

class BookListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BookService()

    def get(self, request):
        logger.info(f"Listing books for user {request.user.username}")
        books = self.service.list_books(request.user)
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        logger.info(f"Creating book for user {request.user.username}")
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            book = self.service.create_book(request.user, serializer.validated_data)
            logger.info(f"Book created successfully: {book.id}")
            return Response(BookSerializer(book).data, status=status.HTTP_201_CREATED)
        logger.warning(f"Failed to create book: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BookDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = BookService()

    def get(self, request, pk):
        logger.info(f"Fetching book {pk} for user {request.user.username}")
        book = self.service.get_book(request.user, pk)
        serializer = BookSerializer(book)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        logger.info(f"Updating book {pk} for user {request.user.username}")
        serializer = BookSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            book = self.service.update_book(request.user, pk, serializer.validated_data)
            logger.info(f"Book updated successfully: {book.id}")
            return Response(BookSerializer(book).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        logger.info(f"Soft deleting book {pk} for user {request.user.username}")
        self.service.delete_book(request.user, pk)
        logger.info(f"Book deleted successfully: {pk}")
        return Response(status=status.HTTP_204_NO_CONTENT)
