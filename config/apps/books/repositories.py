from django.core.exceptions import ObjectDoesNotExist
from .models import Book

class BookRepository:
    def create_book(self, user, **data):
        return Book.objects.create(user=user, **data)

    def get_all_books(self, user):
        return Book.objects.filter(user=user, is_deleted=False)

    def get_book_by_id(self, user, book_id):
        try:
            return Book.objects.get(id=book_id, user=user, is_deleted=False)
        except ObjectDoesNotExist:
            return None

    def update_book(self, book, **data):
        for key, value in data.items():
            setattr(book, key, value)
        book.save()
        return book

    def soft_delete_book(self, book):
        book.is_deleted = True
        book.save()
        return book
