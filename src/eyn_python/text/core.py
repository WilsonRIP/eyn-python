from __future__ import annotations

import re
import string
from typing import List, Dict, Any, Optional, Union
from collections import Counter
import unicodedata
from difflib import SequenceMatcher
import hashlib

from eyn_python.logging import get_logger

log = get_logger(__name__)


def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
    return re.findall(url_pattern, text)


def extract_phone_numbers(text: str) -> List[str]:
    """Extract phone numbers from text."""
    # Various phone number patterns
    patterns = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890
        r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',  # (123) 456-7890
        r'\b\+\d{1,3}\s*\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # +1 123-456-7890
        r'\b\d{10,11}\b',  # 1234567890 or 11234567890
    ]
    
    phone_numbers = []
    for pattern in patterns:
        phone_numbers.extend(re.findall(pattern, text))
    
    return phone_numbers


def extract_credit_cards(text: str) -> List[str]:
    """Extract credit card numbers from text (basic pattern matching)."""
    # Note: This is for educational purposes. Real credit card validation is more complex.
    card_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    return re.findall(card_pattern, text)


def extract_ips(text: str) -> List[str]:
    """Extract IP addresses from text."""
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ips = re.findall(ip_pattern, text)
    
    # Validate IP addresses
    valid_ips = []
    for ip in ips:
        parts = ip.split('.')
        if all(0 <= int(part) <= 255 for part in parts):
            valid_ips.append(ip)
    
    return valid_ips


def clean_text(text: str, remove_punctuation: bool = False, 
               remove_numbers: bool = False, remove_whitespace: bool = True) -> str:
    """Clean and normalize text."""
    # Remove extra whitespace
    if remove_whitespace:
        text = ' '.join(text.split())
    
    # Remove punctuation
    if remove_punctuation:
        text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remove numbers
    if remove_numbers:
        text = re.sub(r'\d+', '', text)
    
    return text.strip()


def normalize_text(text: str) -> str:
    """Normalize text (lowercase, remove extra spaces, etc.)."""
    # Convert to lowercase
    text = text.lower()
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKC', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text.strip()


def remove_stopwords(text: str, custom_stopwords: Optional[List[str]] = None) -> str:
    """Remove common stopwords from text."""
    # Common English stopwords
    default_stopwords = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
        'had', 'what', 'said', 'each', 'which', 'she', 'do', 'how', 'their',
        'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so', 'some',
        'her', 'would', 'make', 'like', 'into', 'him', 'time', 'two',
        'more', 'go', 'no', 'way', 'could', 'my', 'than', 'first', 'been',
        'call', 'who', 'its', 'now', 'find', 'long', 'down', 'day', 'did',
        'get', 'come', 'made', 'may', 'part'
    }
    
    stopwords = default_stopwords
    if custom_stopwords:
        stopwords.update(custom_stopwords)
    
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in stopwords]
    
    return ' '.join(filtered_words)


def extract_keywords(text: str, top_n: int = 10, min_length: int = 3) -> List[tuple[str, int]]:
    """Extract keywords from text based on frequency."""
    # Clean and normalize text
    text = normalize_text(text)
    text = remove_stopwords(text)
    
    # Remove short words
    words = [word for word in text.split() if len(word) >= min_length]
    
    # Count word frequencies
    word_counts = Counter(words)
    
    # Return top N keywords
    return word_counts.most_common(top_n)


def summarize_text(text: str, max_sentences: int = 3) -> str:
    """Create a simple text summary based on sentence importance."""
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= max_sentences:
        return text
    
    # Simple scoring based on word frequency
    word_counts = Counter(normalize_text(text).split())
    
    sentence_scores = []
    for sentence in sentences:
        score = sum(word_counts.get(word.lower(), 0) for word in sentence.split())
        sentence_scores.append((sentence, score))
    
    # Sort by score and take top sentences
    sentence_scores.sort(key=lambda x: x[1], reverse=True)
    top_sentences = sentence_scores[:max_sentences]
    
    # Sort by original order
    top_sentences.sort(key=lambda x: sentences.index(x[0]))
    
    return '. '.join(sentence for sentence, _ in top_sentences) + '.'


def detect_language(text: str) -> Dict[str, float]:
    """Simple language detection based on character frequency."""
    # This is a basic implementation. For production, use libraries like langdetect
    
    # Character frequency patterns for different languages
    patterns = {
        'english': {'e': 12.02, 't': 9.10, 'a': 8.12, 'o': 7.68, 'i': 7.31},
        'spanish': {'e': 13.68, 'a': 12.53, 'o': 8.68, 's': 7.98, 'n': 6.71},
        'french': {'e': 14.71, 'a': 7.58, 's': 7.95, 'i': 7.31, 'n': 7.12},
        'german': {'e': 16.93, 'n': 10.53, 'i': 8.02, 's': 7.23, 'r': 6.89}
    }
    
    # Count characters in text
    text_lower = text.lower()
    char_counts = Counter(char for char in text_lower if char.isalpha())
    total_chars = sum(char_counts.values())
    
    if total_chars == 0:
        return {'unknown': 1.0}
    
    # Calculate character frequencies
    char_freq = {char: count / total_chars * 100 for char, count in char_counts.items()}
    
    # Compare with language patterns
    scores = {}
    for lang, pattern in patterns.items():
        score = 0
        for char, freq in pattern.items():
            if char in char_freq:
                score += 1 - abs(freq - char_freq[char]) / freq
        scores[lang] = score / len(pattern)
    
    # Normalize scores
    total_score = sum(scores.values())
    if total_score > 0:
        scores = {lang: score / total_score for lang, score in scores.items()}
    else:
        scores = {'unknown': 1.0}
    
    return scores


def translate_text(text: str, target_lang: str = 'en', source_lang: str = 'auto') -> str:
    """Translate text using a simple dictionary approach."""
    # This is a placeholder. For production, use libraries like googletrans
    
    # Simple word translations (very limited)
    translations = {
        'hello': {'es': 'hola', 'fr': 'bonjour', 'de': 'hallo'},
        'goodbye': {'es': 'adiós', 'fr': 'au revoir', 'de': 'auf wiedersehen'},
        'thank you': {'es': 'gracias', 'fr': 'merci', 'de': 'danke'},
        'yes': {'es': 'sí', 'fr': 'oui', 'de': 'ja'},
        'no': {'es': 'no', 'fr': 'non', 'de': 'nein'}
    }
    
    words = text.lower().split()
    translated_words = []
    
    for word in words:
        if word in translations and target_lang in translations[word]:
            translated_words.append(translations[word][target_lang])
        else:
            translated_words.append(word)
    
    return ' '.join(translated_words)


def extract_named_entities(text: str) -> Dict[str, List[str]]:
    """Extract named entities from text (basic implementation)."""
    entities = {
        'names': [],
        'organizations': [],
        'locations': [],
        'dates': [],
        'numbers': []
    }
    
    # Extract names (capitalized words)
    name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    entities['names'] = re.findall(name_pattern, text)
    
    # Extract organizations (words with Inc, Corp, Ltd, etc.)
    org_pattern = r'\b[A-Z][a-zA-Z\s]+(?:Inc|Corp|Ltd|LLC|Company|Organization)\b'
    entities['organizations'] = re.findall(org_pattern, text)
    
    # Extract dates
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b'
    entities['dates'] = re.findall(date_pattern, text)
    
    # Extract numbers
    number_pattern = r'\b\d+(?:\.\d+)?\b'
    entities['numbers'] = re.findall(number_pattern, text)
    
    return entities


def sentiment_analysis(text: str) -> Dict[str, float]:
    """Basic sentiment analysis based on word lists."""
    # Simple sentiment word lists
    positive_words = {
        'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
        'awesome', 'brilliant', 'perfect', 'love', 'like', 'happy', 'joy',
        'beautiful', 'nice', 'best', 'better', 'super', 'outstanding'
    }
    
    negative_words = {
        'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'dislike',
        'sad', 'angry', 'frustrated', 'disappointed', 'upset', 'annoying',
        'stupid', 'useless', 'waste', 'problem', 'issue', 'wrong'
    }
    
    # Normalize text
    text = normalize_text(text)
    words = text.split()
    
    # Count positive and negative words
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    total_words = len(words)
    
    if total_words == 0:
        return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
    
    positive_score = positive_count / total_words
    negative_score = negative_count / total_words
    neutral_score = 1.0 - positive_score - negative_score
    
    return {
        'positive': positive_score,
        'negative': negative_score,
        'neutral': neutral_score
    }


def text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts."""
    # Normalize texts
    text1 = normalize_text(text1)
    text2 = normalize_text(text2)
    
    # Use SequenceMatcher for similarity
    similarity = SequenceMatcher(None, text1, text2).ratio()
    
    return similarity


def format_text(text: str, width: int = 80, justify: bool = False) -> str:
    """Format text with specified width and justification."""
    import textwrap
    
    if justify:
        # Justify text (add spaces to make lines equal width)
        lines = textwrap.wrap(text, width=width)
        justified_lines = []
        
        for line in lines[:-1]:  # Don't justify the last line
            if len(line) < width:
                words = line.split()
                if len(words) > 1:
                    spaces_needed = width - len(line)
                    gaps = len(words) - 1
                    spaces_per_gap = spaces_needed // gaps
                    extra_spaces = spaces_needed % gaps
                    
                    formatted_line = words[0]
                    for i, word in enumerate(words[1:], 1):
                        spaces = spaces_per_gap + (1 if i <= extra_spaces else 0)
                        formatted_line += ' ' * spaces + word
                    
                    justified_lines.append(formatted_line)
                else:
                    justified_lines.append(line)
            else:
                justified_lines.append(line)
        
        justified_lines.append(lines[-1])  # Add last line without justification
        return '\n'.join(justified_lines)
    else:
        # Simple wrapping
        return textwrap.fill(text, width=width)


def validate_text(text: str, min_length: int = 1, max_length: int = 10000,
                 allowed_chars: Optional[str] = None, 
                 required_patterns: Optional[List[str]] = None,
                 forbidden_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
    """Validate text against various criteria."""
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Check length
    if len(text) < min_length:
        validation_result['valid'] = False
        validation_result['errors'].append(f"Text too short (minimum {min_length} characters)")
    
    if len(text) > max_length:
        validation_result['valid'] = False
        validation_result['errors'].append(f"Text too long (maximum {max_length} characters)")
    
    # Check allowed characters
    if allowed_chars:
        invalid_chars = set(text) - set(allowed_chars)
        if invalid_chars:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Invalid characters found: {invalid_chars}")
    
    # Check required patterns
    if required_patterns:
        for pattern in required_patterns:
            if not re.search(pattern, text):
                validation_result['valid'] = False
                validation_result['errors'].append(f"Required pattern not found: {pattern}")
    
    # Check forbidden patterns
    if forbidden_patterns:
        for pattern in forbidden_patterns:
            if re.search(pattern, text):
                validation_result['valid'] = False
                validation_result['errors'].append(f"Forbidden pattern found: {pattern}")
    
    # Check for common issues
    if text.count('  ') > 0:
        validation_result['warnings'].append("Multiple consecutive spaces found")
    
    if text.count('\t') > 0:
        validation_result['warnings'].append("Tab characters found")
    
    return validation_result
