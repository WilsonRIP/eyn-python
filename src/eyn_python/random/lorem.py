from __future__ import annotations

import random
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class LoremOptions:
    """Options for lorem ipsum generation."""
    seed: Optional[int] = None
    start_with_lorem: bool = True
    include_punctuation: bool = True
    sentence_variance: bool = True  # Vary sentence length
    paragraph_variance: bool = True  # Vary paragraph length


class LoremGenerator:
    """Lorem ipsum text generator with variations."""
    
    # Classic Lorem Ipsum words
    LOREM_WORDS = [
        "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit",
        "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore",
        "magna", "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud",
        "exercitation", "ullamco", "laboris", "nisi", "aliquip", "ex", "ea", "commodo",
        "consequat", "duis", "aute", "irure", "in", "reprehenderit", "voluptate",
        "velit", "esse", "cillum", "fugiat", "nulla", "pariatur", "excepteur", "sint",
        "occaecat", "cupidatat", "non", "proident", "sunt", "culpa", "qui", "officia",
        "deserunt", "mollit", "anim", "id", "est", "laborum", "at", "vero", "eos",
        "accusamus", "accusantium", "doloremque", "laudantium", "totam", "rem",
        "aperiam", "eaque", "ipsa", "quae", "ab", "illo", "inventore", "veritatis",
        "et", "quasi", "architecto", "beatae", "vitae", "dicta", "sunt", "explicabo",
        "nemo", "ipsam", "voluptatem", "quia", "voluptas", "aspernatur", "aut",
        "odit", "fugit", "sed", "quia", "consequuntur", "magni", "dolores", "eos",
        "qui", "ratione", "voluptatem", "sequi", "nesciunt", "neque", "porro",
        "quisquam", "est", "qui", "dolorem", "ipsum", "quia", "dolor", "sit",
        "amet", "consectetur", "adipisci", "velit", "sed", "quia", "non", "numquam",
        "eius", "modi", "tempora", "incidunt", "ut", "labore", "et", "dolore",
        "magnam", "aliquam", "quaerat", "voluptatem", "ut", "enim", "ad", "minima",
        "veniam", "quis", "nostrum", "exercitationem", "ullam", "corporis",
        "suscipit", "laboriosam", "nisi", "ut", "aliquid", "ex", "ea", "commodi",
        "consequatur", "quis", "autem", "vel", "eum", "iure", "reprehenderit",
        "qui", "in", "ea", "voluptate", "velit", "esse", "quam", "nihil",
        "molestiae", "consequatur", "vel", "illum", "qui", "dolorem", "eum",
        "fugiat", "quo", "voluptas", "nulla", "pariatur"
    ]
    
    # Alternative word sets for variation
    BUSINESS_WORDS = [
        "business", "strategy", "management", "leadership", "innovation", "growth",
        "development", "marketing", "sales", "customer", "service", "quality",
        "performance", "efficiency", "productivity", "success", "achievement",
        "objective", "goal", "target", "mission", "vision", "value", "solution",
        "opportunity", "challenge", "advantage", "benefit", "profit", "revenue",
        "investment", "return", "stakeholder", "partnership", "collaboration",
        "team", "organization", "company", "corporation", "enterprise", "industry",
        "market", "competition", "analysis", "research", "data", "information",
        "technology", "digital", "platform", "system", "process", "workflow"
    ]
    
    TECH_WORDS = [
        "technology", "software", "hardware", "system", "platform", "application",
        "program", "code", "development", "programming", "algorithm", "data",
        "database", "server", "network", "cloud", "computing", "artificial",
        "intelligence", "machine", "learning", "automation", "digital", "cyber",
        "security", "encryption", "protocol", "framework", "library", "api",
        "interface", "user", "experience", "design", "frontend", "backend",
        "full-stack", "mobile", "web", "responsive", "scalable", "performance",
        "optimization", "deployment", "integration", "testing", "debugging",
        "version", "control", "repository", "commit", "merge", "branch"
    ]
    
    def __init__(self, options: LoremOptions = LoremOptions()):
        self.options = options
        if options.seed is not None:
            random.seed(options.seed)
    
    def words(self, count: int, word_set: str = "lorem") -> List[str]:
        """Generate random words."""
        word_dict = {
            "lorem": self.LOREM_WORDS,
            "business": self.BUSINESS_WORDS,
            "tech": self.TECH_WORDS,
        }
        
        source_words = word_dict.get(word_set, self.LOREM_WORDS)
        
        if self.options.start_with_lorem and word_set == "lorem" and count > 0:
            # Always start with "Lorem ipsum"
            result = ["Lorem", "ipsum"]
            remaining = max(0, count - 2)
            if remaining > 0:
                result.extend(random.choices(source_words, k=remaining))
            return result[:count]
        else:
            selected_words = random.choices(source_words, k=count)
            if selected_words:
                selected_words[0] = selected_words[0].capitalize()
            return selected_words
    
    def sentence(self, min_words: int = 5, max_words: int = 15, word_set: str = "lorem") -> str:
        """Generate a random sentence."""
        if self.options.sentence_variance:
            word_count = random.randint(min_words, max_words)
        else:
            word_count = (min_words + max_words) // 2
        
        words = self.words(word_count, word_set)
        sentence = " ".join(words)
        
        if self.options.include_punctuation:
            # Add some commas randomly
            if len(words) > 8:
                comma_positions = random.sample(range(2, len(words) - 2), 
                                               min(2, len(words) // 4))
                for pos in sorted(comma_positions, reverse=True):
                    words[pos] += ","
                sentence = " ".join(words)
            
            sentence += "."
        
        return sentence
    
    def sentences(self, count: int, min_words: int = 5, max_words: int = 15, 
                  word_set: str = "lorem") -> List[str]:
        """Generate multiple sentences."""
        return [self.sentence(min_words, max_words, word_set) for _ in range(count)]
    
    def paragraph(self, min_sentences: int = 3, max_sentences: int = 8, 
                  min_words: int = 5, max_words: int = 15, word_set: str = "lorem") -> str:
        """Generate a paragraph."""
        if self.options.paragraph_variance:
            sentence_count = random.randint(min_sentences, max_sentences)
        else:
            sentence_count = (min_sentences + max_sentences) // 2
        
        sentences = self.sentences(sentence_count, min_words, max_words, word_set)
        return " ".join(sentences)
    
    def paragraphs(self, count: int, min_sentences: int = 3, max_sentences: int = 8,
                   min_words: int = 5, max_words: int = 15, word_set: str = "lorem") -> List[str]:
        """Generate multiple paragraphs."""
        paragraphs_list = []
        for i in range(count):
            # Only start with "Lorem ipsum" in the first paragraph
            current_options = self.options
            if i > 0 and word_set == "lorem":
                # Temporarily disable "start with lorem" for subsequent paragraphs
                temp_options = LoremOptions(
                    seed=self.options.seed,
                    start_with_lorem=False,
                    include_punctuation=self.options.include_punctuation,
                    sentence_variance=self.options.sentence_variance,
                    paragraph_variance=self.options.paragraph_variance
                )
                temp_generator = LoremGenerator(temp_options)
                paragraph = temp_generator.paragraph(min_sentences, max_sentences, 
                                                   min_words, max_words, word_set)
            else:
                paragraph = self.paragraph(min_sentences, max_sentences, 
                                         min_words, max_words, word_set)
            
            paragraphs_list.append(paragraph)
        
        return paragraphs_list
    
    def text(self, paragraphs: int = 3, sentences_per_paragraph: tuple = (3, 8),
             words_per_sentence: tuple = (5, 15), word_set: str = "lorem",
             separator: str = "\n\n") -> str:
        """Generate formatted lorem ipsum text."""
        min_sentences, max_sentences = sentences_per_paragraph
        min_words, max_words = words_per_sentence
        
        paragraph_list = self.paragraphs(paragraphs, min_sentences, max_sentences,
                                       min_words, max_words, word_set)
        
        return separator.join(paragraph_list)
    
    def title(self, min_words: int = 2, max_words: int = 6, word_set: str = "lorem") -> str:
        """Generate a title-case lorem ipsum title."""
        word_count = random.randint(min_words, max_words)
        words = self.words(word_count, word_set)
        
        # Title case (capitalize all words)
        title_words = [word.capitalize() for word in words]
        return " ".join(title_words)
    
    def slug(self, word_count: int = 3, word_set: str = "lorem") -> str:
        """Generate a URL-friendly slug."""
        words = self.words(word_count, word_set)
        return "-".join(word.lower() for word in words)
    
    def list_items(self, count: int, item_type: str = "sentence", 
                   word_set: str = "lorem") -> List[str]:
        """Generate a list of items."""
        items = []
        for _ in range(count):
            if item_type == "sentence":
                item = self.sentence(3, 10, word_set)
            elif item_type == "phrase":
                words = self.words(random.randint(2, 5), word_set)
                item = " ".join(words).capitalize()
            elif item_type == "word":
                item = random.choice(self.words(1, word_set)).capitalize()
            else:
                item = self.sentence(3, 10, word_set)
            
            items.append(item)
        
        return items


# Convenience functions
def generate_lorem_words(count: int, word_set: str = "lorem", 
                        options: LoremOptions = LoremOptions()) -> List[str]:
    """Generate lorem ipsum words."""
    generator = LoremGenerator(options)
    return generator.words(count, word_set)


def generate_lorem_sentences(count: int, min_words: int = 5, max_words: int = 15,
                            word_set: str = "lorem", options: LoremOptions = LoremOptions()) -> List[str]:
    """Generate lorem ipsum sentences."""
    generator = LoremGenerator(options)
    return generator.sentences(count, min_words, max_words, word_set)


def generate_lorem_paragraphs(count: int, min_sentences: int = 3, max_sentences: int = 8,
                             word_set: str = "lorem", options: LoremOptions = LoremOptions()) -> List[str]:
    """Generate lorem ipsum paragraphs."""
    generator = LoremGenerator(options)
    return generator.paragraphs(count, min_sentences, max_sentences, word_set=word_set)


def generate_lorem_text(paragraphs: int = 3, sentences_per_paragraph: tuple = (3, 8),
                       words_per_sentence: tuple = (5, 15), word_set: str = "lorem",
                       separator: str = "\n\n", options: LoremOptions = LoremOptions()) -> str:
    """Generate formatted lorem ipsum text."""
    generator = LoremGenerator(options)
    return generator.text(paragraphs, sentences_per_paragraph, words_per_sentence, 
                         word_set, separator)
