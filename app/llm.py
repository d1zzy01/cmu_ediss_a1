from __future__ import annotations

import logging

from google import genai
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Book

logger = logging.getLogger(__name__)


def request_summary(book: Book) -> str:
    if not settings.gemini_api_key:
        logger.warning("Skipping summary generation for ISBN %s because GEMINI_API_KEY is not set", book.isbn)
        return ""

    prompt = (
        "Write a concise summary of about 500 words for this book. "
        "Use the metadata provided and avoid markdown.\n"
        f"ISBN: {book.isbn}\n"
        f"Title: {book.title}\n"
        f"Author: {book.author}\n"
        f"Description: {book.description}\n"
        f"Genre: {book.genre}"
    )
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    logger.info("Generated summary for ISBN %s", book.isbn)
    return response.text or ""


def populate_book_summary(isbn: str) -> None:
    db: Session = SessionLocal()
    try:
        book = db.get(Book, isbn)
        if not book:
            return
        try:
            # Summary failures should not break the book creation flow.
            book.summary = request_summary(book)
        except Exception as exc:
            logger.exception("Summary generation failed for ISBN %s: %s", isbn, exc)
            book.summary = ""
        db.add(book)
        db.commit()
    finally:
        db.close()
