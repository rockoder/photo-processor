from enum import Enum

class Status(str, Enum):
	pending = 'pending'
	processing = 'processing'
	completed = 'completed'
	failed = 'failed'
