from __future__ import annotations

import random
import statistics
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
import math


@dataclass
class DiceRoll:
    """Result of a dice roll."""
    dice_notation: str
    individual_rolls: List[int]
    total: int
    modifier: int = 0
    final_total: int = 0
    
    def __post_init__(self):
        if self.final_total == 0:
            self.final_total = self.total + self.modifier


@dataclass
class DiceStats:
    """Statistics for dice rolls."""
    min_possible: int
    max_possible: int
    average: float
    most_likely: int
    probability_distribution: Dict[int, float]
    
    
@dataclass
class Dice:
    """Dice configuration."""
    count: int = 1
    sides: int = 6
    modifier: int = 0
    drop_lowest: int = 0
    drop_highest: int = 0
    exploding: bool = False  # Roll again on max value
    reroll_on: List[int] = field(default_factory=list)  # Reroll these values once
    advantage: bool = False  # Roll twice, take higher
    disadvantage: bool = False  # Roll twice, take lower
    
    def __post_init__(self):
        if self.advantage and self.disadvantage:
            raise ValueError("Cannot have both advantage and disadvantage")
        if self.drop_lowest + self.drop_highest >= self.count:
            raise ValueError("Cannot drop more dice than rolled")
    
    @property
    def notation(self) -> str:
        """Get dice notation string."""
        notation = f"{self.count}d{self.sides}"
        
        if self.drop_lowest > 0:
            notation += f"dl{self.drop_lowest}"
        if self.drop_highest > 0:
            notation += f"dh{self.drop_highest}"
        if self.exploding:
            notation += "!"
        if self.reroll_on:
            notation += f"r{','.join(map(str, self.reroll_on))}"
        if self.advantage:
            notation += " (advantage)"
        if self.disadvantage:
            notation += " (disadvantage)"
        if self.modifier != 0:
            sign = "+" if self.modifier >= 0 else ""
            notation += f"{sign}{self.modifier}"
        
        return notation
    
    def roll(self, seed: Optional[int] = None) -> DiceRoll:
        """Roll the dice."""
        if seed is not None:
            random.seed(seed)
        
        if self.advantage or self.disadvantage:
            # Roll twice
            roll1 = self._single_roll_set()
            roll2 = self._single_roll_set()
            
            total1 = sum(roll1)
            total2 = sum(roll2)
            
            if self.advantage:
                if total1 >= total2:
                    individual_rolls = roll1
                    total = total1
                else:
                    individual_rolls = roll2
                    total = total2
            else:  # disadvantage
                if total1 <= total2:
                    individual_rolls = roll1
                    total = total1
                else:
                    individual_rolls = roll2
                    total = total2
        else:
            individual_rolls = self._single_roll_set()
            total = sum(individual_rolls)
        
        return DiceRoll(
            dice_notation=self.notation,
            individual_rolls=individual_rolls,
            total=total,
            modifier=self.modifier,
            final_total=total + self.modifier
        )
    
    def _single_roll_set(self) -> List[int]:
        """Roll a single set of dice."""
        rolls = []
        
        for _ in range(self.count):
            roll = self._single_die_roll()
            rolls.append(roll)
        
        # Apply dropping rules
        if self.drop_lowest > 0 or self.drop_highest > 0:
            sorted_rolls = sorted(rolls)
            if self.drop_lowest > 0:
                sorted_rolls = sorted_rolls[self.drop_lowest:]
            if self.drop_highest > 0:
                sorted_rolls = sorted_rolls[:-self.drop_highest]
            rolls = sorted_rolls
        
        return rolls
    
    def _single_die_roll(self) -> int:
        """Roll a single die with all modifiers."""
        roll = random.randint(1, self.sides)
        
        # Handle rerolls
        if roll in self.reroll_on:
            roll = random.randint(1, self.sides)
        
        # Handle exploding dice
        if self.exploding:
            total = roll
            while roll == self.sides:
                roll = random.randint(1, self.sides)
                total += roll
            return total
        
        return roll
    
    def statistics(self) -> DiceStats:
        """Calculate theoretical statistics for this dice configuration."""
        # For complex dice (exploding, advantage/disadvantage), use simulation
        if (self.exploding or self.advantage or self.disadvantage or 
            self.reroll_on or self.drop_lowest > 0 or self.drop_highest > 0):
            return self._simulate_statistics()
        
        # Simple case: standard dice
        min_roll = self.count
        max_roll = self.count * self.sides
        average = self.count * (self.sides + 1) / 2
        
        # Calculate probability distribution for simple dice
        distribution = {}
        for total in range(min_roll, max_roll + 1):
            probability = self._calculate_probability(total)
            distribution[total + self.modifier] = probability
        
        # Find most likely outcome
        most_likely = max(distribution.keys(), key=lambda k: distribution[k])
        
        return DiceStats(
            min_possible=min_roll + self.modifier,
            max_possible=max_roll + self.modifier,
            average=average + self.modifier,
            most_likely=most_likely,
            probability_distribution=distribution
        )
    
    def _calculate_probability(self, target: int) -> float:
        """Calculate probability of rolling a specific total (simple dice only)."""
        # This is a simplified calculation for standard dice
        # For a more accurate calculation, we'd need to use generating functions
        if self.count == 1:
            return 1.0 / self.sides if 1 <= target <= self.sides else 0.0
        
        # For multiple dice, approximate using normal distribution
        mean = self.count * (self.sides + 1) / 2
        variance = self.count * (self.sides**2 - 1) / 12
        std_dev = math.sqrt(variance)
        
        # Normal approximation with continuity correction
        z1 = (target - 0.5 - mean) / std_dev
        z2 = (target + 0.5 - mean) / std_dev
        
        # Approximate normal CDF
        def normal_cdf(z):
            return 0.5 * (1 + math.erf(z / math.sqrt(2)))
        
        probability = normal_cdf(z2) - normal_cdf(z1)
        return max(0.0, probability)
    
    def _simulate_statistics(self, simulations: int = 10000) -> DiceStats:
        """Calculate statistics through simulation."""
        results = []
        for _ in range(simulations):
            roll = self.roll()
            results.append(roll.final_total)
        
        min_result = min(results)
        max_result = max(results)
        average = statistics.mean(results)
        
        # Count occurrences for probability distribution
        counter = Counter(results)
        total_rolls = len(results)
        distribution = {value: count / total_rolls for value, count in counter.items()}
        
        most_likely = max(distribution.keys(), key=lambda k: distribution[k])
        
        return DiceStats(
            min_possible=min_result,
            max_possible=max_result,
            average=average,
            most_likely=most_likely,
            probability_distribution=distribution
        )


def parse_dice_notation(notation: str) -> Dice:
    """Parse dice notation string into Dice object."""
    # Remove spaces
    notation = notation.replace(" ", "")
    
    # Extract modifier
    modifier = 0
    if "+" in notation:
        parts = notation.split("+")
        notation = parts[0]
        modifier = int(parts[1])
    elif "-" in notation and notation.count("-") == 1:
        parts = notation.split("-")
        notation = parts[0]
        modifier = -int(parts[1])
    
    # Parse basic dice (XdY)
    if "d" not in notation.lower():
        raise ValueError("Invalid dice notation: missing 'd'")
    
    dice_part = notation.lower()
    
    # Extract special modifiers
    exploding = "!" in dice_part
    dice_part = dice_part.replace("!", "")
    
    drop_lowest = 0
    if "dl" in dice_part:
        parts = dice_part.split("dl")
        dice_part = parts[0]
        drop_lowest = int(parts[1]) if parts[1] else 1
    
    drop_highest = 0
    if "dh" in dice_part:
        parts = dice_part.split("dh")
        dice_part = parts[0]
        drop_highest = int(parts[1]) if parts[1] else 1
    
    reroll_on = []
    if "r" in dice_part:
        parts = dice_part.split("r")
        dice_part = parts[0]
        if len(parts) > 1:
            reroll_values = parts[1].split(",")
            reroll_on = [int(v) for v in reroll_values if v.isdigit()]
    
    # Parse count and sides
    parts = dice_part.split("d")
    count = int(parts[0]) if parts[0] else 1
    sides = int(parts[1])
    
    return Dice(
        count=count,
        sides=sides,
        modifier=modifier,
        drop_lowest=drop_lowest,
        drop_highest=drop_highest,
        exploding=exploding,
        reroll_on=reroll_on
    )


def roll_dice(notation: str, seed: Optional[int] = None) -> DiceRoll:
    """Roll dice from notation string."""
    dice = parse_dice_notation(notation)
    return dice.roll(seed)


def roll_custom_dice(count: int, sides: int, modifier: int = 0, 
                    seed: Optional[int] = None) -> DiceRoll:
    """Roll custom dice configuration."""
    dice = Dice(count=count, sides=sides, modifier=modifier)
    return dice.roll(seed)


def roll_with_modifier(base_notation: str, modifier: int, 
                      seed: Optional[int] = None) -> DiceRoll:
    """Roll dice with additional modifier."""
    dice = parse_dice_notation(base_notation)
    dice.modifier += modifier
    return dice.roll(seed)


def roll_advantage(notation: str, seed: Optional[int] = None) -> DiceRoll:
    """Roll with advantage (twice, take higher)."""
    dice = parse_dice_notation(notation)
    dice.advantage = True
    return dice.roll(seed)


def roll_disadvantage(notation: str, seed: Optional[int] = None) -> DiceRoll:
    """Roll with disadvantage (twice, take lower)."""
    dice = parse_dice_notation(notation)
    dice.disadvantage = True
    return dice.roll(seed)


def calculate_dice_stats(notation: str) -> DiceStats:
    """Calculate statistics for dice notation."""
    dice = parse_dice_notation(notation)
    return dice.statistics()


def roll_multiple(notation: str, count: int, seed: Optional[int] = None) -> List[DiceRoll]:
    """Roll the same dice multiple times."""
    if seed is not None:
        random.seed(seed)
    
    dice = parse_dice_notation(notation)
    rolls = []
    
    for _ in range(count):
        roll = dice.roll()
        rolls.append(roll)
    
    return rolls


def compare_dice_sets(notation1: str, notation2: str, trials: int = 1000) -> Dict[str, float]:
    """Compare two dice sets statistically."""
    dice1 = parse_dice_notation(notation1)
    dice2 = parse_dice_notation(notation2)
    
    wins1 = 0
    wins2 = 0
    ties = 0
    
    for _ in range(trials):
        roll1 = dice1.roll()
        roll2 = dice2.roll()
        
        if roll1.final_total > roll2.final_total:
            wins1 += 1
        elif roll2.final_total > roll1.final_total:
            wins2 += 1
        else:
            ties += 1
    
    return {
        f"{notation1}_wins": wins1 / trials,
        f"{notation2}_wins": wins2 / trials,
        "ties": ties / trials,
        f"{notation1}_win_percentage": (wins1 / (trials - ties)) * 100 if ties < trials else 0,
        f"{notation2}_win_percentage": (wins2 / (trials - ties)) * 100 if ties < trials else 0,
    }


def generate_dice_table(notation: str, rolls: int = 100) -> Dict[int, int]:
    """Generate frequency table for dice rolls."""
    dice = parse_dice_notation(notation)
    results = Counter()
    
    for _ in range(rolls):
        roll = dice.roll()
        results[roll.final_total] += 1
    
    return dict(results)


# Common dice shortcuts
def d4(count: int = 1, modifier: int = 0, seed: Optional[int] = None) -> DiceRoll:
    """Roll d4 dice."""
    return roll_custom_dice(count, 4, modifier, seed)


def d6(count: int = 1, modifier: int = 0, seed: Optional[int] = None) -> DiceRoll:
    """Roll d6 dice."""
    return roll_custom_dice(count, 6, modifier, seed)


def d8(count: int = 1, modifier: int = 0, seed: Optional[int] = None) -> DiceRoll:
    """Roll d8 dice."""
    return roll_custom_dice(count, 8, modifier, seed)


def d10(count: int = 1, modifier: int = 0, seed: Optional[int] = None) -> DiceRoll:
    """Roll d10 dice."""
    return roll_custom_dice(count, 10, modifier, seed)


def d12(count: int = 1, modifier: int = 0, seed: Optional[int] = None) -> DiceRoll:
    """Roll d12 dice."""
    return roll_custom_dice(count, 12, modifier, seed)


def d20(count: int = 1, modifier: int = 0, seed: Optional[int] = None) -> DiceRoll:
    """Roll d20 dice."""
    return roll_custom_dice(count, 20, modifier, seed)


def d100(count: int = 1, modifier: int = 0, seed: Optional[int] = None) -> DiceRoll:
    """Roll d100 dice."""
    return roll_custom_dice(count, 100, modifier, seed)
