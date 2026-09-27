# Authentication & Token Configuration
DEFAULT_TOKEN_LEEWAY_SECONDS: int = 120

# Role Constants
ROLE_ADMIN: str = "Admin"
ROLE_MANAGER: str = "Manager"
ROLE_EMPLOYEE: str = "Employee"

# Employee Status Constants
EMPLOYEE_STATUS_ACTIVE: str = "ACTIVE"
EMPLOYEE_STATUS_INACTIVE: str = "INACTIVE"

# Employment Types
EMPLOYMENT_TYPES: tuple[str, ...] = ("Full-Time", "Part-Time", "Contract", "Intern")

# Floor Map Defaults
DEFAULT_MAP_WIDTH: int = 1000
DEFAULT_MAP_HEIGHT: int = 800

# Seat Status Constants
SEAT_STATUS_VACANT: str = "Vacant"
SEAT_STATUS_OCCUPIED: str = "Occupied"
SEAT_STATUS_BLOCKED: str = "Blocked"

# Seat Types
SEAT_TYPE_STANDARD: str = "Standard"
SEAT_TYPE_CUBICLE: str = "Cubicle"

# Seat History Actions
SEAT_ACTION_ASSIGN: str = "ASSIGN"
SEAT_ACTION_RELEASE: str = "RELEASE"
SEAT_ACTION_RELOCATE: str = "RELOCATE"
SEAT_ACTION_SWAP: str = "SWAP"

# Permission Request Types
REQUEST_TYPE_NEW_SEAT: str = "NEW_SEAT"
REQUEST_TYPE_RELOCATION: str = "RELOCATION"
REQUEST_TYPE_SWAP: str = "SWAP"

# Permission Request Statuses
REQUEST_STATUS_PENDING: str = "PENDING"
REQUEST_STATUS_MANAGER_APPROVED: str = "MANAGER_APPROVED"
REQUEST_STATUS_REJECTED: str = "REJECTED"
REQUEST_STATUS_COMPLETED: str = "COMPLETED"
REQUEST_STATUS_CANCELLED: str = "CANCELLED"

