from enum import Enum


class EnumRoles(str, Enum):
    """Enum class representing the possible roles for an user."""

    ADMIN = "Admin"
    BEGINNER = "Beginner"
    EXPERT = "Expert"
    RESEARCHER = "Researcher"
    DEMO = "Demo"
    DELETED_USER = "Deleted"
    
    def __str__(self) -> str:
        """Return string representation of a EnumRoles object.

        Returns
            str: string value of the enumeration

        """
        return self.value

