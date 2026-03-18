from rest_framework.exceptions import NotFound
from .repositories import BookRepository

class BookService:
    def __init__(self):
        self.repository = BookRepository()

    def create_book(self, user, data):
        return self.repository.create_book(user, **data)

    def list_books(self, user):
        return self.repository.get_all_books(user)

    def get_book(self, user, book_id):
        book = self.repository.get_book_by_id(user, book_id)
        if not book:
            raise NotFound(detail="Book not found or deleted")
        return book

    def update_book(self, user, book_id, data):
        book = self.get_book(user, book_id)
        return self.repository.update_book(book, **data)

    def delete_book(self, user, book_id):
        book = self.get_book(user, book_id)
        return self.repository.soft_delete_book(book)
