# Project home page

Open `site/index.html` directly or serve only `site/` with a local static server. The page
explains the current template, shows an actual CLI example, links documentation, and offers
an enterprise hosting inquiry through `.github/ISSUE_TEMPLATE/hosting.yml`.

When creating an app, replace the name, description, tested command/output, owner/repo links,
and hosting contact route. Describe implemented behavior; do not advertise planned features
as shipping. Add an approved email/contact URL if a private inquiry channel is wanted. GitHub
issues are visible to repository readers; the form explicitly excludes confidential information.

## Publication

The page is committed for review. No public website is enabled by this change. The
repository remains private. For GitHub Pages, first review the exact page and intended
access, check the account's private-repo Pages entitlement, and configure Pages to use GitHub
Actions. Copy `templates/github/pages.yml` into `.github/workflows/` after review, configure the
`github-pages` environment and `PAGES_ENABLED=true`, then dispatch from the default branch.
Only `site/` is uploaded. A private source repository does not automatically make a Pages
website private; verify the deployed access model before enabling it. Use another static host
if the chosen Pages setup cannot meet the intended visibility or use case.

Keep this an informational page. Application login, checkout/payment and hosted enterprise
functionality need an appropriate app host and separate implementation plans. No analytics,
external fonts or contact-form data collection ship by default.

Acceptance: narrow/wide layouts, keyboard navigation, readable contrast, real command output,
working source/contact links after merge, no private material in the site artifact.
[GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).
