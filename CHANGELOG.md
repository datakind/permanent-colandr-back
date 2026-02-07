# CHANGELOG

## v1.1 (unreleased)

### new

- added rate-limiting to protect the API from abuse, and result-caching to improve performance of common database lookups
- added an API endpoint to re-send registration confirmation emails, in case the original was not acted upon and subsequently lost
- added an API endpoint to deduplicate studies, without requiring a new citation file import
- allowed reviews to have multiple "owners", and made it manageable by the owner(s)
- added support for specifying the numbers of reviewers per study for a _percentage_ of studies in a given review, rather than always requiring the same number for all studies; and added support for filtering studies by the number of reviewers
- added functionality for admin users to add other admin users

### improved

- across-the-board improvements in performance and stability of the system
- streamlined and standardized the underlying data models powering the application
- improved scalability and correctness of parsing citations from uploaded files
- improved speed and accuracy of text extraction from uploaded study PDFs
- re-wrote study deduplication system using a different approach, which is faster and more scalable
- updated study ranker model and its interface, and implemented its usage in a more efficient way
- ported data extraction functionality (including ML models) from a side-car Scala system into the main Python system
- refactored, standardized, and upgraded user authentication and authorization systems, for better application security
- increased study tags' and screening reasons' maximum lengths, from 25 to 64 characters, to allow for more descriptive values
- moved several admin-only endpoints into a separate API path
- improved styling and content of user emails

### fixed

- actually forbid changes to "frozen" reviews
- prevented non-admin users from granting themselves admin privileges

### development

- containerized all back-end services for more convenient, consistent builds and deployments, on whatever system
- repackaged `colandr` to follow current best practice, including consolidated configuration in `pyproject.toml`, adding a license file, and managing the package/environment with `uv`
- added an extensive unit testing suite, and set up CI workflows to automatically build, test, lint, and type-check source code
- migrated the API framework from `flask-restplus` to `flask-restx` to `apiflask`
- upgraded all 3rd-party packages to current (or close enough) versions, pulling in performance improvements, security fixes, and other benefits
- upgraded the database system from Postgres v9 to v17, and minimum Python from v3.7 to v3.11
- generalized filesystem storage functionality to allow storing data in Google Cloud Storage in addition to just local disk
- removed lots of "cruft", from HTML template files to outdated configurations to Scala side-car systems
