1. **Create an account:** Enter the user name, email, and password.
1. **Create a new systematic review project:** Enter the review's name and description. Invite collaborators to join the project (optional).
1. **Plan out the project:** Enter an objective; research questions; Population, Intervention, Comparator, and Outcome (PICO); key terms; and citation selection criteria with labels and descriptions.
    - App uses key terms to automatically build a boolean search query.
1. **Collect citations of candidate studies:** Search data sources using boolean search query and save basic bibliographic data aka "citations". [_outside of app workflow_]
1. **Enter citations data:** Either upload collections of citations in RIS or BibTex file format, or manually enter bibliographic data.
    - App automatically handles data standardization, sanitization, and de-duplication.
1. **Screen citations by expected relevance to review:** Inspect title, abstract, and key terms; based on selection criteria, mark citations as "included" or "excluded". If excluded, give the criteria for the decision.
    - App automatically ranks citations by expected relevance, from high to low. Various NLP techniques and strategies are used at different points in the process, depending on the number of citations screened, observed inclusion rate, and other factors.
1. **Collect additional citations and adjust boolean search query (project key terms), as needed**
    - App automatically suggests key terms to include or exclude based on results of citation screening.
1. **Screen all citations, or until some relevance threshold is no longer met**: Projects may require more than one screener per citation before a decision is made.
1. **Download full-text versions of all included citations** [_outside of app workflow (probably)_]
