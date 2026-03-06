from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    async def run(self, context: dict) -> dict:
        """Process context and return enriched context dict.

        Set context["passed"] = False to short-circuit the pipeline.
        """
        ...
