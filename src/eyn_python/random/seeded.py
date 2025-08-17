from __future__ import annotations

import random
from typing import List, TypeVar, Optional, Any, Sequence
from dataclasses import dataclass


T = TypeVar('T')


@dataclass
class SeededRandom:
    """Seeded random number generator for reproducible results."""
    seed: int
    
    def __post_init__(self):
        self._random = random.Random(self.seed)
    
    def reseed(self, seed: int) -> None:
        """Change the seed and reset the generator."""
        self.seed = seed
        self._random = random.Random(seed)
    
    def int(self, min_val: int = 0, max_val: int = 2**31 - 1) -> int:
        """Generate seeded random integer."""
        return self._random.randint(min_val, max_val)
    
    def float(self, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Generate seeded random float."""
        return self._random.uniform(min_val, max_val)
    
    def choice(self, sequence: Sequence[T]) -> T:
        """Make seeded random choice from sequence."""
        if not sequence:
            raise ValueError("Cannot choose from empty sequence")
        return self._random.choice(sequence)
    
    def choices(self, population: Sequence[T], k: int = 1, 
                weights: Optional[List[float]] = None) -> List[T]:
        """Make seeded random choices with replacement."""
        return self._random.choices(population, weights=weights, k=k)
    
    def sample(self, population: Sequence[T], k: int) -> List[T]:
        """Make seeded random sample without replacement."""
        return self._random.sample(population, k)
    
    def shuffle(self, sequence: List[T]) -> List[T]:
        """Shuffle sequence with seeded randomness."""
        result = sequence.copy()
        self._random.shuffle(result)
        return result
    
    def boolean(self, probability: float = 0.5) -> bool:
        """Generate seeded random boolean."""
        return self._random.random() < probability
    
    def bytes(self, length: int) -> bytes:
        """Generate seeded random bytes."""
        return bytes(self._random.getrandbits(8) for _ in range(length))
    
    def string(self, length: int, alphabet: str = "abcdefghijklmnopqrstuvwxyz") -> str:
        """Generate seeded random string."""
        return ''.join(self._random.choice(alphabet) for _ in range(length))
    
    def hex_string(self, length: int) -> str:
        """Generate seeded random hex string."""
        hex_chars = "0123456789abcdef"
        return self.string(length, hex_chars)
    
    def gaussian(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Generate seeded random value from Gaussian distribution."""
        return self._random.gauss(mu, sigma)
    
    def exponential(self, lambd: float = 1.0) -> float:
        """Generate seeded random value from exponential distribution."""
        return self._random.expovariate(lambd)
    
    def uniform_list(self, count: int, min_val: float = 0.0, max_val: float = 1.0) -> List[float]:
        """Generate list of seeded random uniform values."""
        return [self.float(min_val, max_val) for _ in range(count)]
    
    def int_list(self, count: int, min_val: int = 0, max_val: int = 100) -> List[int]:
        """Generate list of seeded random integers."""
        return [self.int(min_val, max_val) for _ in range(count)]
    
    def weighted_choice(self, choices: List[T], weights: List[float]) -> T:
        """Make weighted choice with seeded randomness."""
        if len(choices) != len(weights):
            raise ValueError("Choices and weights must have same length")
        return self._random.choices(choices, weights=weights, k=1)[0]
    
    def permutation(self, sequence: Sequence[T]) -> List[T]:
        """Generate random permutation with seeded randomness."""
        return self.shuffle(list(sequence))
    
    def partition(self, total: int, parts: int) -> List[int]:
        """Randomly partition a total into parts with seeded randomness."""
        if parts <= 0:
            raise ValueError("Parts must be positive")
        if total < 0:
            raise ValueError("Total must be non-negative")
        
        if parts == 1:
            return [total]
        
        # Generate random partition points
        partition_points = sorted([self.int(0, total) for _ in range(parts - 1)])
        partition_points = [0] + partition_points + [total]
        
        # Calculate partition sizes
        partition_sizes = []
        for i in range(len(partition_points) - 1):
            partition_sizes.append(partition_points[i + 1] - partition_points[i])
        
        return partition_sizes
    
    def coordinates(self, count: int, x_range: tuple = (0, 100), 
                   y_range: tuple = (0, 100)) -> List[tuple]:
        """Generate random 2D coordinates with seeded randomness."""
        x_min, x_max = x_range
        y_min, y_max = y_range
        
        coordinates = []
        for _ in range(count):
            x = self.float(x_min, x_max)
            y = self.float(y_min, y_max)
            coordinates.append((x, y))
        
        return coordinates
    
    def color_rgb(self) -> tuple:
        """Generate random RGB color with seeded randomness."""
        return (self.int(0, 255), self.int(0, 255), self.int(0, 255))
    
    def color_hex(self) -> str:
        """Generate random hex color with seeded randomness."""
        r, g, b = self.color_rgb()
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def matrix(self, rows: int, cols: int, min_val: float = 0.0, max_val: float = 1.0) -> List[List[float]]:
        """Generate random matrix with seeded randomness."""
        return [[self.float(min_val, max_val) for _ in range(cols)] for _ in range(rows)]


# Global seeded generators for convenience
_global_generators = {}


def get_seeded_generator(seed: int) -> SeededRandom:
    """Get or create a global seeded generator."""
    if seed not in _global_generators:
        _global_generators[seed] = SeededRandom(seed)
    return _global_generators[seed]


def seeded_int(seed: int, min_val: int = 0, max_val: int = 2**31 - 1) -> int:
    """Generate seeded random integer."""
    generator = get_seeded_generator(seed)
    return generator.int(min_val, max_val)


def seeded_float(seed: int, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Generate seeded random float."""
    generator = get_seeded_generator(seed)
    return generator.float(min_val, max_val)


def seeded_choice(seed: int, sequence: Sequence[T]) -> T:
    """Make seeded random choice."""
    generator = get_seeded_generator(seed)
    return generator.choice(sequence)


def seeded_shuffle(seed: int, sequence: List[T]) -> List[T]:
    """Shuffle sequence with seeded randomness."""
    generator = get_seeded_generator(seed)
    return generator.shuffle(sequence)


def seeded_sample(seed: int, population: Sequence[T], k: int) -> List[T]:
    """Make seeded random sample."""
    generator = get_seeded_generator(seed)
    return generator.sample(population, k)


def seeded_boolean(seed: int, probability: float = 0.5) -> bool:
    """Generate seeded random boolean."""
    generator = get_seeded_generator(seed)
    return generator.boolean(probability)


def seeded_string(seed: int, length: int, alphabet: str = "abcdefghijklmnopqrstuvwxyz") -> str:
    """Generate seeded random string."""
    generator = get_seeded_generator(seed)
    return generator.string(length, alphabet)


def seeded_coordinates(seed: int, count: int, x_range: tuple = (0, 100), 
                      y_range: tuple = (0, 100)) -> List[tuple]:
    """Generate seeded random coordinates."""
    generator = get_seeded_generator(seed)
    return generator.coordinates(count, x_range, y_range)


def seeded_partition(seed: int, total: int, parts: int) -> List[int]:
    """Partition total into parts with seeded randomness."""
    generator = get_seeded_generator(seed)
    return generator.partition(total, parts)


def seeded_color_hex(seed: int) -> str:
    """Generate seeded random hex color."""
    generator = get_seeded_generator(seed)
    return generator.color_hex()


def seeded_gaussian(seed: int, mu: float = 0.0, sigma: float = 1.0) -> float:
    """Generate seeded Gaussian random value."""
    generator = get_seeded_generator(seed)
    return generator.gaussian(mu, sigma)


def deterministic_sequence(seed: int, length: int, sequence_type: str = "int", 
                          **kwargs) -> List[Any]:
    """Generate deterministic sequence of values."""
    generator = SeededRandom(seed)
    
    if sequence_type == "int":
        min_val = kwargs.get("min_val", 0)
        max_val = kwargs.get("max_val", 100)
        return generator.int_list(length, min_val, max_val)
    elif sequence_type == "float":
        min_val = kwargs.get("min_val", 0.0)
        max_val = kwargs.get("max_val", 1.0)
        return generator.uniform_list(length, min_val, max_val)
    elif sequence_type == "boolean":
        probability = kwargs.get("probability", 0.5)
        return [generator.boolean(probability) for _ in range(length)]
    elif sequence_type == "choice":
        choices = kwargs.get("choices", ["A", "B", "C"])
        return [generator.choice(choices) for _ in range(length)]
    else:
        raise ValueError(f"Unknown sequence type: {sequence_type}")


def reproducible_shuffle_multiple(seed: int, *sequences) -> tuple:
    """Shuffle multiple sequences with same randomness."""
    generator = SeededRandom(seed)
    
    # Create indices and shuffle them
    if not sequences:
        return ()
    
    length = len(sequences[0])
    if not all(len(seq) == length for seq in sequences):
        raise ValueError("All sequences must have the same length")
    
    indices = list(range(length))
    generator.shuffle(indices)
    
    # Apply the same shuffle to all sequences
    result = []
    for sequence in sequences:
        shuffled = [sequence[i] for i in indices]
        result.append(shuffled)
    
    return tuple(result)
