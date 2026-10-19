# DTJ search report, 2026-10-14

Mode: **shadow** (dry run). Site: https://digitaltusharjoshi.com. Pages checked: 24.

## 1. Website check

3 to fix now, 52 to fix soon, 49 for later. Source: https://digitaltusharjoshi.com/sitemap_index.xml and each listed page, fetched by site_scan.py.

| Priority | Problem | Page | What we saw |
|---|---|---|---|
| Fix now | template-in-sitemap | https://digitaltusharjoshi.com/elementor-hf/footer/ | a theme building block (header/footer template) is listed for Google as a page |
| Fix now | template-in-sitemap | https://digitaltusharjoshi.com/elementor-hf/header/ | a theme building block (header/footer template) is listed for Google as a page |
| Fix now | wordpress-default-page | https://digitaltusharjoshi.com/sample-page/ | WordPress's default page is listed for Google |
| Fix soon | author-archive | https://digitaltusharjoshi.com/author/dream-dev/ | posts are credited to the login name in the URL |
| Fix soon | description-grammar | https://digitaltusharjoshi.com/ | 'DTJ is a Data-Driven Digital Marketing Services Agency in India, We Helping Brands Grow With Social Media, SEO, Meta Ads' |
| Fix soon | description-missing | https://digitaltusharjoshi.com/about-us/ | no meta description |
| Fix soon | description-missing | https://digitaltusharjoshi.com/blogs/ | no meta description |
| Fix soon | description-missing | https://digitaltusharjoshi.com/career/ | no meta description |
| Fix soon | description-missing | https://digitaltusharjoshi.com/case-studies/ | no meta description |
| Fix soon | description-missing | https://digitaltusharjoshi.com/category/blogs/ | no meta description |
| Fix soon | description-missing | https://digitaltusharjoshi.com/contact-us/ | no meta description |
| Fix soon | description-missing | https://digitaltusharjoshi.com/how-to-scale-d2c-brands-using-meta-ads-from-%e2%82%b91-lakh | no meta description |

92 more in scan.json.

## 2. Fixes waiting for one yes (batch `fix-2026-10-14`)

4 changes ready to apply, 0 written but stopped by the checks, 6 for a person.

| Id | Change | Page | Now | After |
|---|---|---|---|---|
| c001 | Hide from Google | https://digitaltusharjoshi.com/elementor-hf/footer/ | index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1 | noindex |
| c002 | Hide from Google | https://digitaltusharjoshi.com/elementor-hf/header/ | index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1 | noindex |
| c003 | Hide from Google | https://digitaltusharjoshi.com/sample-page/ | index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1 | noindex |
| c004 | Business details for Google and AI | https://digitaltusharjoshi.com/ | (empty) | business details for Rajkot and Ahmedabad offices |

**To apply:** Harsh (or a teammate by name when he can't be reached) says yes to this batch, then run GitHub > Actions >
"SEO apply fixes" with this run's number and your name, or in Claude Code:
`python -m seo_engine.apply_batch --batch <this folder>/fixes.json --approved-by "<name>"` (add `--only c001,c002` to apply some).

For a person:
- llms.txt is made by Yoast from the site title and tagline: an administrator changes the tagline in Settings > General to a plain line (e.g. 'Performance marketing for D2C brands'). DTJ decides the wording. (1 page(s))
- Yoast > Settings > Advanced > Author archives: off; and credit posts to a real person or 'DTJ Team' (Users > the author's display name). Needs an administrator. (1 page(s))
- These pages need exactly one main heading (H1): in Elementor, set the page's top heading to H1 and the others to H2. (18 page(s))
- Add 3-5 founder questions as headings, each answered in its first sentence. (13 page(s))
- Say more on these pages: proof, steps and FAQs. (3 page(s))
- Two posts make claims we can't source ('India's Best ... Agency', 'Why 90% of D2C Brands Fail'): DTJ decides to keep, reword or remove them. The engine never touches them.

## 3. Do AI assistants name DTJ?

Not run this week (planned 10 questions). It needs the Claude API key and/or the DataForSEO login.

## 4. Keyword plan

No plan yet: made on the first live run with the DataForSEO login (then every 28 days).

## 5. City pages

0 built, 0 ready to write, cities still needing real proof: Ahmedabad, Rajkot, Surat, Vadodara.
Each city needs at least one client from there who agreed to be named (with a result) plus an office, a review or a photo (services/seo-engine/seo_engine/data/local_proof.json).

## 6. This week's page

Planned article: "My Facebook and Instagram ads are running but I get no orders. What should I check first?" (topics.json). Not written (needs the Claude API key and --live).

## 7. Notes

- 15 pages need a new title or description: written on a live run (needs the Claude API key).
- 10 images need alt text: written on a live run.

## 8. For a person

- Say yes (or no) to the fixes batch above.
- Review the draft and press Publish in WordPress (one yes per page).
- Google Business Profiles for Rajkot and Ahmedabad: the address and phone exactly as on the contact page.
- Ask happy clients for a Google review that names the service and the city; add city clients to local_proof.json.
