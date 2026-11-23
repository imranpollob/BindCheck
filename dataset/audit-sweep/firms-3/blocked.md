# blocked

- 2026-11-22 Cyfrin commits history https://github.com/Cyfrin/cyfrin-audit-reports/commits/main -> HTTP 429 (rate-limit) after ~290 requests in ~40 min to github.com/raw. Backing off; switching to non-GitHub sources.
- 2026-11-22 Hacken https://hacken.io/audits/ -> HTTP 403 Cloudflare "Just a moment" challenge (bot check). Not bypassed.
- 2026-11-22 CertiK https://skynet.certik.com/ -> HTTP 403 captcha page; www.certik.com/audits and /search?q= -> 404 (no public index reachable by curl). Not bypassed.
