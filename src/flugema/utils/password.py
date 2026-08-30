import re

class PasswordChecker:
    """Check password strength with a length-dependent character-type requirement.

    The longer the password, the fewer character families it must contain.
    """

    MIN_LENGTH = 10

    # Default policy: (minimum length, number of required character families).
    # Sorted from longest to shortest: the first matching rule wins.
    DEFAULT_TIERS = (
        (30, 1),   # >= 30 characters: a single family is enough (passphrase)
        (20, 2),
        (15, 3),
        (MIN_LENGTH, 4),   # 10-15 characters: all 4 families are required
    )

    DEFAULT_FAMILIES = {
        "lowercase": r"[a-z]",
        "uppercase": r"[A-Z]",
        "digit": r"\d",
        "special character": r"[^A-Za-z0-9]",
    }

    @classmethod
    def required_families(cls, length: int) -> int | None:
        """Return the number of character families required for the given length."""
        for min_length, families_count in cls.DEFAULT_TIERS:
            if length >= min_length:
                return families_count
        return None

    @classmethod
    def found_families(cls, password: str) -> set[str]:
        """Return the character families present in the password."""
        found_families = []
        for name in cls.DEFAULT_FAMILIES:
            pattern = cls.DEFAULT_FAMILIES[name]
            if re.search(pattern, password):
                found_families.append(name)
        return found_families

    @classmethod
    def check(cls, password: str) -> False:
        """Check a password and return a detailed result."""
        if not isinstance(password, str) or not password:
            return False

        errors: list[str] = []

        if password != password.strip():
            return False

        length = len(password)
        if length < cls.MIN_LENGTH:
            return False

        found    = cls.found_families(password)
        required = cls.required_families(length)

        if len(found) < required:
            return False

        return True
