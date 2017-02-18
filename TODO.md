## Burton

- [x] Remove `fields` param from certain API endpoints, e.g. PUT `reviews/{id}/plan` and change logic to check for `if not missing`
- [x] Standardize and clean up logging throughout app
- [x] Enable admin access throughout app
- [x] Delete full-text PDFs upon review deletion
- [x] Re-organize colandr_data directory to have review-specific sub-directories

Longer term:

- [ ] Better handle uploaded fulltext file naming; maybe just store file format in db?
- [ ] enable https everywhere (via [let's encrypt](https://letsencrypt.org/)?)
- [ ] Add extra fields in users table, e.g. affiliation
- [ ] Consider using something like Flask-Security for more comprehensive and less home-rolled user login and management
- [ ] Watch for flask-restplus to integrate webargs validation, which would probably make auto-docs much easier and less redundant
- [ ] API rate-limiting
- [ ] Confirm that password reset actually works o_O
