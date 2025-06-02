from dataclasses import dataclass


@dataclass
class Metadata:
    """
    Metadata model.

    Attributes:
        record (int): Identifier for record (usually recordId).
        metadata (str): The label name of the metadata returned  (e.x. biome).
        value (str): The label of the metadata returned  (e.x. forest).
        sentence (str): Context from where the ML model predicted the value.
        sentence_location (int): The location in the fulltext sentence can be found.
        confidence (float): The probability under the model for the returned label.
        confidence_level (int): The confidence level.
    """
    record: int
    metadata: str
    value: str
    sentence: str
    sentence_location: int
    confidence: float
    confidence_level: int = -1
