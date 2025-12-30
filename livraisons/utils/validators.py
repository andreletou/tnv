from django.core.exceptions import ValidationError

class MaxSizeValidator:
    def __init__(self, max_size):
        self.max_size = max_size

    def __call__(self, value):
        if value.size > self.max_size:
            raise ValidationError(f'Taille max: {self.max_size//(1024*1024)}MB')