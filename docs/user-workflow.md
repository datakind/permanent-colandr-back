### User Workflow

1. **Create an account:** Enter user name, email, and password. Verify account via confirmation email.
1. **Create a new systematic review:** Enter the review's name and description. Invite collaborators to join the project via email (optional).
1. **Plan the systematic review:** Enter an objective; research questions; Population, Intervention, Comparator, and Outcome (PICO); key terms; study selection criteria; and data to extract from selected studies.
    - colandr automatically generates a boolean search query from key terms.
1. **Collect citations for candidate studies:** Search databases using boolean query, plus sources of gray literature. Save studies' bibliographic data (aka citations) in standard RIS or BibTeX format. [_Outside of colandr's scope._]
1. **Import citations data:** Upload collections of citations from file(s) and/or manually enter bibliographic data one at a time. Repeat this and previous step as necessary.
    - colandr automatically handles data standardization, sanitization, and de-duplication.
1. **Screen citations:** Inspect title, abstract, and keywords for each study. Based on selection criteria, choose to "include" or "exclude" studies, and provide reasons. Screen in batches and (optionally) with co-screeners until no unscreened citations remain. More than one screener per citation may be required before a final decision is made.
    - colandr provides a variety of filters, plus intelligent sorting by expected relevance to the systematic review.
1. **Update review key terms (and boolean query) as needed:** To ensure quality of review, add and/or remove key terms. In case of changes, return to step 4 and continue forward.
    - colandr automatically suggests good/bad key terms based on the (ongoing) results of citation screening.
1. **Collect full-text content of all included studies:** Gather PDFs or texts from available data sources. [_Outside of colandr's scope._]
1. **Upload full-texts data:** Upload PDF or text for each included study, one at a time.
    - colandr automatically extracts and stores the content.
1. **Screen full-texts:** Inspect the full-text content for each study. Proceed as when screening citations.
1. **Extract data from included studies:** From full-text study content, extract structured data relevant to the systematic review, as defined in the review planning step.
    - colandr automatically suggests sentences relevant to particular extraction domains.
1. **Export systematic review results:** Save extracted data, bibliographic data of included studies, and number of studies at each step of the process to disk. Publish a paper.
