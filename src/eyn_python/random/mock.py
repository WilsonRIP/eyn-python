from __future__ import annotations

import random
import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    ANY = "any"


class Locale(Enum):
    EN_US = "en_US"
    EN_GB = "en_GB"
    ES_ES = "es_ES"
    FR_FR = "fr_FR"
    DE_DE = "de_DE"
    IT_IT = "it_IT"


@dataclass
class MockDataOptions:
    """Options for mock data generation."""
    locale: Locale = Locale.EN_US
    seed: Optional[int] = None
    include_null_chance: float = 0.0  # Chance of returning None/null values


class MockDataGenerator:
    """Comprehensive mock data generator."""
    
    # Sample data sets
    FIRST_NAMES = {
        Gender.MALE: [
            "James", "John", "Robert", "Michael", "David", "William", "Richard", "Joseph",
            "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Mark",
            "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
            "George", "Timothy", "Ronald", "Jason", "Edward", "Jeffrey", "Ryan", "Jacob",
            "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott",
            "Brandon", "Benjamin", "Samuel", "Gregory", "Alexander", "Patrick", "Frank"
        ],
        Gender.FEMALE: [
            "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
            "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Helen", "Sandra",
            "Donna", "Carol", "Ruth", "Sharon", "Michelle", "Laura", "Sarah", "Kimberly",
            "Deborah", "Dorothy", "Lisa", "Nancy", "Karen", "Betty", "Helen", "Sandra",
            "Donna", "Carol", "Ruth", "Sharon", "Michelle", "Laura", "Emily", "Ashley",
            "Emma", "Olivia", "Sophia", "Ava", "Isabella", "Mia", "Abigail", "Madison"
        ]
    }
    
    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
        "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
        "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell"
    ]
    
    DOMAINS = [
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com",
        "example.com", "test.com", "mail.com", "email.com", "protonmail.com"
    ]
    
    STREET_NAMES = [
        "Main", "Oak", "Pine", "Maple", "Cedar", "Elm", "Washington", "Lake", "Hill",
        "Park", "River", "Church", "Spring", "School", "State", "High", "Market",
        "Union", "Water", "North", "South", "East", "West", "Center", "Mill"
    ]
    
    STREET_TYPES = ["St", "Ave", "Dr", "Ln", "Rd", "Blvd", "Ct", "Pl", "Way", "Cir"]
    
    CITIES = [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
        "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
        "Fort Worth", "Columbus", "Indianapolis", "Charlotte", "San Francisco",
        "Seattle", "Denver", "Washington", "Boston", "El Paso", "Detroit", "Nashville",
        "Portland", "Memphis", "Oklahoma City", "Las Vegas", "Louisville", "Baltimore"
    ]
    
    STATES = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
        "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
        "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
    ]
    
    COMPANIES = [
        "Tech Corp", "Global Systems", "Innovation Labs", "Digital Solutions", "Future Works",
        "Data Dynamics", "Cloud Services", "Smart Technologies", "Next Gen", "Alpha Beta",
        "Quantum Computing", "Cyber Security", "AI Research", "Blockchain Solutions",
        "Green Energy", "BioTech Labs", "Nano Materials", "Space Exploration"
    ]
    
    COMPANY_SUFFIXES = ["Inc", "LLC", "Corp", "Ltd", "Co", "Group", "Solutions", "Systems"]
    
    def __init__(self, options: MockDataOptions = MockDataOptions()):
        self.options = options
        if options.seed is not None:
            random.seed(options.seed)
    
    def _maybe_null(self, value: Any) -> Optional[Any]:
        """Return None based on null chance, otherwise return value."""
        if self.options.include_null_chance > 0 and random.random() < self.options.include_null_chance:
            return None
        return value
    
    def first_name(self, gender: Gender = Gender.ANY) -> Optional[str]:
        """Generate a random first name."""
        if gender == Gender.ANY:
            gender = random.choice([Gender.MALE, Gender.FEMALE])
        
        name = random.choice(self.FIRST_NAMES[gender])
        return self._maybe_null(name)
    
    def last_name(self) -> Optional[str]:
        """Generate a random last name."""
        name = random.choice(self.LAST_NAMES)
        return self._maybe_null(name)
    
    def full_name(self, gender: Gender = Gender.ANY) -> Optional[str]:
        """Generate a random full name."""
        first = self.first_name(gender)
        last = self.last_name()
        if first is None or last is None:
            return None
        return f"{first} {last}"
    
    def email(self, first_name: Optional[str] = None, last_name: Optional[str] = None) -> Optional[str]:
        """Generate a random email address."""
        if first_name is None:
            first_name = self.first_name()
        if last_name is None:
            last_name = self.last_name()
        
        if first_name is None or last_name is None:
            return None
        
        domain = random.choice(self.DOMAINS)
        
        # Various email formats
        formats = [
            f"{first_name.lower()}.{last_name.lower()}@{domain}",
            f"{first_name.lower()}{last_name.lower()}@{domain}",
            f"{first_name[0].lower()}{last_name.lower()}@{domain}",
            f"{first_name.lower()}{random.randint(1, 999)}@{domain}",
        ]
        
        email = random.choice(formats)
        return self._maybe_null(email)
    
    def phone(self, format: str = "###-###-####") -> Optional[str]:
        """Generate a random phone number."""
        phone_number = ""
        for char in format:
            if char == "#":
                phone_number += str(random.randint(0, 9))
            else:
                phone_number += char
        
        return self._maybe_null(phone_number)
    
    def address(self) -> Optional[Dict[str, str]]:
        """Generate a random address."""
        street_number = random.randint(1, 9999)
        street_name = random.choice(self.STREET_NAMES)
        street_type = random.choice(self.STREET_TYPES)
        city = random.choice(self.CITIES)
        state = random.choice(self.STATES)
        zip_code = f"{random.randint(10000, 99999)}"
        
        address_data = {
            "street": f"{street_number} {street_name} {street_type}",
            "city": city,
            "state": state,
            "zip": zip_code,
            "country": "USA"
        }
        
        return self._maybe_null(address_data)
    
    def company(self) -> Optional[str]:
        """Generate a random company name."""
        if random.choice([True, False]):
            # Use predefined company name
            company = random.choice(self.COMPANIES)
        else:
            # Generate company name from last names
            name = random.choice(self.LAST_NAMES)
            company = f"{name} {random.choice(self.COMPANY_SUFFIXES)}"
        
        return self._maybe_null(company)
    
    def user_profile(self, gender: Gender = Gender.ANY) -> Optional[Dict[str, Any]]:
        """Generate a complete user profile."""
        first = self.first_name(gender)
        last = self.last_name()
        
        if first is None or last is None:
            return None
        
        profile = {
            "first_name": first,
            "last_name": last,
            "full_name": f"{first} {last}",
            "email": self.email(first, last),
            "phone": self.phone(),
            "address": self.address(),
            "company": self.company(),
            "job_title": self.job_title(),
            "birth_date": self.birth_date(),
            "gender": gender.value if gender != Gender.ANY else random.choice([Gender.MALE, Gender.FEMALE]).value,
        }
        
        return self._maybe_null(profile)
    
    def job_title(self) -> Optional[str]:
        """Generate a random job title."""
        titles = [
            "Software Engineer", "Product Manager", "Data Scientist", "UX Designer",
            "Marketing Manager", "Sales Representative", "Account Executive",
            "Business Analyst", "Project Manager", "DevOps Engineer", "Quality Assurance",
            "Technical Writer", "HR Manager", "Financial Analyst", "Operations Manager",
            "Customer Success Manager", "Research Scientist", "System Administrator"
        ]
        
        title = random.choice(titles)
        return self._maybe_null(title)
    
    def birth_date(self, min_age: int = 18, max_age: int = 80) -> Optional[datetime.date]:
        """Generate a random birth date."""
        today = datetime.date.today()
        min_date = today - datetime.timedelta(days=max_age * 365)
        max_date = today - datetime.timedelta(days=min_age * 365)
        
        time_between = max_date - min_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        
        birth_date = min_date + datetime.timedelta(days=random_days)
        return self._maybe_null(birth_date)
    
    def credit_card(self) -> Optional[Dict[str, str]]:
        """Generate fake credit card data."""
        # Fake numbers that pass Luhn algorithm
        prefixes = {
            "Visa": ["4"],
            "MasterCard": ["5"],
            "American Express": ["34", "37"],
            "Discover": ["6"]
        }
        
        card_type = random.choice(list(prefixes.keys()))
        prefix = random.choice(prefixes[card_type])
        
        # Generate remaining digits
        if card_type == "American Express":
            length = 15
        else:
            length = 16
        
        number = prefix + ''.join([str(random.randint(0, 9)) for _ in range(length - len(prefix) - 1)])
        
        # Calculate Luhn check digit
        def luhn_check_digit(number):
            digits = [int(d) for d in number]
            for i in range(len(digits) - 2, -1, -2):
                digits[i] *= 2
                if digits[i] > 9:
                    digits[i] -= 9
            total = sum(digits)
            return str((10 - (total % 10)) % 10)
        
        number += luhn_check_digit(number)
        
        # Format number
        if card_type == "American Express":
            formatted_number = f"{number[:4]} {number[4:10]} {number[10:]}"
        else:
            formatted_number = f"{number[:4]} {number[4:8]} {number[8:12]} {number[12:]}"
        
        # Generate expiry date
        current_year = datetime.date.today().year
        exp_year = random.randint(current_year + 1, current_year + 5)
        exp_month = random.randint(1, 12)
        
        card_data = {
            "type": card_type,
            "number": formatted_number,
            "expiry": f"{exp_month:02d}/{str(exp_year)[2:]}",
            "cvv": str(random.randint(100, 999)),
            "holder_name": self.full_name()
        }
        
        return self._maybe_null(card_data)
    
    def internet_data(self) -> Optional[Dict[str, str]]:
        """Generate internet-related data."""
        username = self.username()
        domain = random.choice(self.DOMAINS)
        
        data = {
            "username": username,
            "email": f"{username}@{domain}",
            "website": f"https://www.{username}.com",
            "ip_address": self.ip_address(),
            "mac_address": self.mac_address(),
            "user_agent": self.user_agent(),
        }
        
        return self._maybe_null(data)
    
    def username(self) -> Optional[str]:
        """Generate a random username."""
        first = self.first_name()
        last = self.last_name()
        
        if first is None or last is None:
            return None
        
        formats = [
            f"{first.lower()}{last.lower()}",
            f"{first.lower()}_{last.lower()}",
            f"{first[0].lower()}{last.lower()}",
            f"{first.lower()}{random.randint(1, 999)}",
            f"{first.lower()}.{last.lower()}",
        ]
        
        username = random.choice(formats)
        return self._maybe_null(username)
    
    def ip_address(self, version: int = 4) -> Optional[str]:
        """Generate a random IP address."""
        if version == 4:
            octets = [str(random.randint(1, 254)) for _ in range(4)]
            ip = ".".join(octets)
        else:  # IPv6
            groups = [f"{random.randint(0, 65535):04x}" for _ in range(8)]
            ip = ":".join(groups)
        
        return self._maybe_null(ip)
    
    def mac_address(self) -> Optional[str]:
        """Generate a random MAC address."""
        mac = [f"{random.randint(0, 255):02x}" for _ in range(6)]
        return self._maybe_null(":".join(mac))
    
    def user_agent(self) -> Optional[str]:
        """Generate a random user agent string."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        ]
        
        agent = random.choice(agents)
        return self._maybe_null(agent)
    
    def datetime_data(self) -> Optional[Dict[str, Any]]:
        """Generate datetime-related data."""
        now = datetime.datetime.now()
        
        # Random dates in the past year
        past_date = now - datetime.timedelta(days=random.randint(1, 365))
        future_date = now + datetime.timedelta(days=random.randint(1, 365))
        
        data = {
            "created_at": past_date,
            "updated_at": now - datetime.timedelta(days=random.randint(1, 30)),
            "expires_at": future_date,
            "timezone": random.choice(["UTC", "EST", "PST", "CST", "MST"]),
            "timestamp": int(past_date.timestamp()),
        }
        
        return self._maybe_null(data)


# Convenience functions
def generate_name(gender: Gender = Gender.ANY, options: MockDataOptions = MockDataOptions()) -> Optional[str]:
    """Generate a random name."""
    generator = MockDataGenerator(options)
    return generator.full_name(gender)


def generate_email(options: MockDataOptions = MockDataOptions()) -> Optional[str]:
    """Generate a random email."""
    generator = MockDataGenerator(options)
    return generator.email()


def generate_phone(format: str = "###-###-####", options: MockDataOptions = MockDataOptions()) -> Optional[str]:
    """Generate a random phone number."""
    generator = MockDataGenerator(options)
    return generator.phone(format)


def generate_address(options: MockDataOptions = MockDataOptions()) -> Optional[Dict[str, str]]:
    """Generate a random address."""
    generator = MockDataGenerator(options)
    return generator.address()


def generate_company(options: MockDataOptions = MockDataOptions()) -> Optional[str]:
    """Generate a random company name."""
    generator = MockDataGenerator(options)
    return generator.company()


def generate_user_profile(gender: Gender = Gender.ANY, options: MockDataOptions = MockDataOptions()) -> Optional[Dict[str, Any]]:
    """Generate a complete user profile."""
    generator = MockDataGenerator(options)
    return generator.user_profile(gender)


def generate_credit_card(options: MockDataOptions = MockDataOptions()) -> Optional[Dict[str, str]]:
    """Generate fake credit card data."""
    generator = MockDataGenerator(options)
    return generator.credit_card()


def generate_internet_data(options: MockDataOptions = MockDataOptions()) -> Optional[Dict[str, str]]:
    """Generate internet-related data."""
    generator = MockDataGenerator(options)
    return generator.internet_data()


def generate_datetime_data(options: MockDataOptions = MockDataOptions()) -> Optional[Dict[str, Any]]:
    """Generate datetime-related data."""
    generator = MockDataGenerator(options)
    return generator.datetime_data()
