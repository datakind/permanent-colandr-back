Citation deduplication training dataset source:

McKeown S, Mir ZM. Considerations for conducting systematic reviews: evaluating the performance of different methods for de-duplicating references. Syst Rev. 2021 Jan 23;10(1):38. doi: 10.1186/s13643-021-01583-y. [link](https://pubmed.ncbi.nlm.nih.gov/33485394/)

Borealis (2021). Evaluating the performance of different methods for de-duplicating references [Dataset]. http://doi.org/10.5683/SP2/5TNOZ4 [link](https://borealisdata.ca/dataset.xhtml?persistentId=doi:10.5683/SP2/5TNOZ4)

Prepared for input to deduper training script with the following code (stored here, for now):

```python
import io
import pathlib
import re

from colandr.lib.fileio import ris

RE_BAD_LINK = re.compile(r"\nLink to the Ovid Full Text or citation:.*?(\n|$)")
RE_BAD_TAG = re.compile(r"\nNL  - .*?\n")
RE_BAD_YEAR = re.compile(r"(\nY1  - \d{4})//\n")

dir_path = pathlib.Path(
    "/Users/burtondewilde/Desktop/projects/datakind__colandr/permanent-colandr-back/colandr_data/dedupe-v2/data"
)
file_paths = [
    file_path.resolve()
    for file_path in dir_path.iterdir()
    if file_path.suffix == ".ris"
]

records = []
for file_path in file_paths:
    with file_path.open(mode="r") as f:
        data = f.read()
        data = RE_BAD_LINK.sub("", data)
        data = RE_BAD_TAG.sub(r"", data)
        data = RE_BAD_YEAR.sub(r"\1\n", data)
        data = data.encode("utf-8")
        records.extend(ris.read(io.BytesIO(data)))

# TODO: train/test split?

with (dir_path / "training.json").open(mode="w") as f:
    json.dump(records, f, indent=4)
```

**OLD**

search query: "climate change" AND adaptation AND politics AND "northeastern united states" AND right-wing
date range: 2020 - 2023

data sources
- Google Scholar: https://scholar.google.com
- CORE: https://core.ac.uk
- Semantic Scholar: https://www.semanticscholar.org
- Clio: https://clio.columbia.edu
- ProQuest: https://www.proquest.com
- JStor: https://www.jstor.org/
