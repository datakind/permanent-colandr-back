# Text Extractors

This module provides functionality for extracting metadata from full text documents.

## Modules

### `locations.py`

Extracts geographical locations mentioned in a text document using spaCy's Named Entity Recognition (NER).

Features:
- Identifies locations (GPE, LOC entities) in text
- Filters out locations that appear in references/citations
- Groups locations by name and ranks by frequency
- Provides context (surrounding sentences) for each location
- Includes confidence scores

### `review_metadata.py`

Extracts metadata fields based on trained models for each review.

Features:
- Review-specific model training based on existing data extractions
- Support for select_one and select_many field types
- Sentence-level classification using River (online machine learning) library
- Confidence scores and levels
- Model caching to improve performance

## API Endpoints

The extractors are used by two new API endpoints:

1. `GET /api/fulltexts/{id}/locations` - Extract locations from a full text
2. `GET /api/fulltexts/{id}/metadata?meta={meta_type}` - Extract all metadata from a full text or filter by specific metadata type

## Usage

```python
from colandr.lib.extractors.locations import get_locations
from colandr.lib.extractors.review_metadata import extract_metadata

# Extract locations
locations = get_locations("Text content with mentions of London and Paris...")

# Extract metadata
metadata = extract_metadata(
    record_id="123",
    review_id=1,
    text="Text content with relevant metadata...",
    metadata_type=None  # Optional filter
)
```

## Implementation Notes

The metadata extraction follows the next workflow:
1. Load data extraction form from review plan
2. Get training data from existing data extractions
3. Train classifiers for each metadata field
4. Predict metadata for new documents

The location extraction also follows a similar workflow:
1. Process text with spaCy NLP
2. Extract location entities
3. Filter out entities in references
4. Group and rank locations by frequency
