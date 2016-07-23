from __future__ import absolute_import, division, print_function, unicode_literals

import io
import json


def load_citation_selection_data(filepath='../data/processed/citation_selection.json'):
    """
    See `notebooks/record-matching.ipynb`.
    """
    with io.open(filepath, mode='rt') as f:
        selection_data = {item['citation_id']: item['included']
                          for item in json.load(f)}
    return selection_data
