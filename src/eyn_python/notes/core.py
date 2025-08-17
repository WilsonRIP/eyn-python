from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
import re
import uuid

from fuzzywuzzy import fuzz
from markdown import markdown

from eyn_python.logging import get_logger

log = get_logger(__name__)

NOTES_DIR_NAME = ".eyn_notes"


@dataclass
class Note:
    id: str
    title: str
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class NoteSearchResult:
    note: Note
    score: float
    matches: Dict[str, List[str]]


def _get_notes_dir() -> Path:
    """Get the directory where notes are stored, creating it if it doesn't exist."""
    home_dir = Path.home()
    notes_dir = home_dir / NOTES_DIR_NAME
    notes_dir.mkdir(parents=True, exist_ok=True)
    return notes_dir


def _note_file_path(note_id: str) -> Path:
    """Construct the path to a note's JSON file."""
    return _get_notes_dir() / f"{note_id}.json"


def _load_note_from_file(file_path: Path) -> Note:
    """Load a Note object from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Convert timestamps back to datetime objects
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    data["updated_at"] = datetime.fromisoformat(data["updated_at"])
    return Note(**data)


def _save_note_to_file(note: Note) -> None:
    """Save a Note object to a JSON file."""
    file_path = _note_file_path(note.id)
    with open(file_path, "w", encoding="utf-8") as f:
        # Serialize datetime objects to ISO format strings
        json.dump(asdict(note), f, default=lambda o: o.isoformat() if isinstance(o, datetime) else o, indent=2)


def create_note(title: str, content: str, tags: Optional[List[str]] = None) -> Note:
    """Create a new note."""
    note_id = str(uuid.uuid4())
    now = datetime.now()
    note = Note(
        id=note_id,
        title=title,
        content=content,
        tags=sorted([t.lower() for t in tags]) if tags else [],
        created_at=now,
        updated_at=now,
    )
    _save_note_to_file(note)
    log.info(f"Created note: {note.title} (ID: {note.id})")
    return note


def get_note(note_id: str) -> Optional[Note]:
    """Retrieve a note by its ID."""
    file_path = _note_file_path(note_id)
    if not file_path.exists():
        log.warning(f"Note with ID {note_id} not found.")
        return None
    return _load_note_from_file(file_path)


def list_notes(tag: Optional[str] = None, limit: Optional[int] = None) -> List[Note]:
    """List all notes, optionally filtered by tag and limited by count."""
    notes: List[Note] = []
    notes_dir = _get_notes_dir()
    for file_path in notes_dir.glob("*.json"):
        try:
            note = _load_note_from_file(file_path)
            if tag is None or tag.lower() in note.tags:
                notes.append(note)
        except Exception as e:
            log.error(f"Failed to load note from {file_path}: {e}")

    # Sort by updated_at, newest first
    notes.sort(key=lambda n: n.updated_at, reverse=True)

    if limit is not None:
        notes = notes[:limit]

    return notes


def search_notes(
    query: str,
    tag_filter: Optional[str] = None,
    case_sensitive: bool = False,
    fuzzy: bool = False,
) -> List[NoteSearchResult]:
    """Search notes by query in title or content, optionally filtered by tag.

    Args:
        query: The search string.
        tag_filter: Optional tag to filter search results.
        case_sensitive: If True, search is case-sensitive.
        fuzzy: If True, uses fuzzy matching for the query.

    Returns:
        A list of NoteSearchResult objects, sorted by relevance score.
    """
    results: List[NoteSearchResult] = []
    notes_to_search = list_notes(tag=tag_filter)

    for note in notes_to_search:
        score = 0.0
        matches: Dict[str, List[str]] = {"title": [], "content": [], "tags": []}

        # Prepare text for search
        search_title = note.title if case_sensitive else note.title.lower()
        search_content = note.content if case_sensitive else note.content.lower()
        search_query = query if case_sensitive else query.lower()

        # Search in title
        if fuzzy:
            title_score = fuzz.partial_ratio(search_query, search_title)
            if title_score > 70:  # Threshold for fuzzy match
                score += title_score
                matches["title"].append(note.title) # Store original title
        elif search_query in search_title:
            score += 100 # Direct match gives high score
            matches["title"].append(note.title)

        # Search in content
        if fuzzy:
            content_score = fuzz.partial_ratio(search_query, search_content)
            if content_score > 70:
                score += content_score * 0.5 # Content matches are less impactful than title
                # Find and store matched lines/snippets
                for line in note.content.splitlines():
                    if search_query in (line if case_sensitive else line.lower()):
                        matches["content"].append(line.strip())
        elif search_query in search_content:
            score += 50 # Direct match
            for line in note.content.splitlines():
                if search_query in (line if case_sensitive else line.lower()):
                    matches["content"].append(line.strip())

        # Tag matching (exact match, case-insensitive if not case_sensitive)
        for tag_item in note.tags:
            compare_tag = tag_item if case_sensitive else tag_item.lower()
            if fuzzy:
                tag_score = fuzz.ratio(search_query, compare_tag)
                if tag_score > 80:
                    score += tag_score * 0.8 # Tags are important
                    matches["tags"].append(tag_item)
            elif search_query == compare_tag:
                score += 80 # Direct tag match is significant
                matches["tags"].append(tag_item)

        if score > 0:
            results.append(NoteSearchResult(note=note, score=score, matches=matches))

    results.sort(key=lambda r: r.score, reverse=True)
    return results


def update_note(
    note_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Optional[Note]:
    """Update an existing note."""
    note = get_note(note_id)
    if note is None:
        log.warning(f"Note with ID {note_id} not found for update.")
        return None

    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
    if tags is not None:
        note.tags = sorted([t.lower() for t in tags])
    note.updated_at = datetime.now()

    _save_note_to_file(note)
    log.info(f"Updated note: {note.title} (ID: {note.id})")
    return note


def delete_note(note_id: str) -> bool:
    """Delete a note by its ID."""
    file_path = _note_file_path(note_id)
    if not file_path.exists():
        log.warning(f"Note with ID {note_id} not found for deletion.")
        return False
    try:
        os.remove(file_path)
        log.info(f"Deleted note file: {note_id}.json")
        return True
    except Exception as e:
        log.error(f"Failed to delete note {note_id}: {e}")
        return False
