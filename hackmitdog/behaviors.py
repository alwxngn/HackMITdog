from dimos.agents.annotation import skill
from dimos.core.module import Module


class DogBehaviors(Module):

    @skill()
    def hello_dog(self) -> str:
        """Simple test behavior."""
        return "Hello from HackMITdog!"


