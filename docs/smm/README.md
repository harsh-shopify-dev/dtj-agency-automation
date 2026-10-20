# DTJ social media automation (SMM)

Built 20 Oct 2026 (Harsh: "build the automation and it should post daily"). Plan and decisions: `2026-10-20-smm-automation-plan.md`.
Code: `services/smm/`. The weekly content session: skill `dtj-smm`.

## What it does
| Step (Harsh's list) | How | Runs |
|---|---|---|
| Research, scripts and captions | Claude Code in the content session, skill `dtj-smm`; one post a day, per-platform words | weekly, a person present |
| Graphics and videos | DTJ templates turned into JPEGs by a browser (`smm render`); ChatGPT backgrounds only; videos from the reel factory | weekly |
| QC | the code gate (`smm check`): numbers only from the proof list, no process/promise/price/jargon words, platform limits, file shapes, AI labels, no repeats, one post a day | weekly + before every yes |
| Deck with the calendar | `smm deck` / `smm submit` (.pptx: calendar + one slide per post) | weekly |
| Final approval | a named yes per post (`smm approve` or GitHub Actions "SMM approve posts"); stores a fingerprint, so a changed post needs a new yes | weekly |
| Scheduled, published | GitHub Actions "SMM daily", hourly 07:05-22:05 IST: posts each approved post when its time comes | daily, no AI |
| Audit results | "SMM daily" at 10:20 IST reads numbers at 24 h and 7 days; Monday report to Telegram | daily, no AI |
| Repeat and scale | next content session starts from the report | weekly |

Where things live: code on the main branch; the posts, approvals, posting records, results and the action log on the data
branch **`smm-content`** (never merged; `services/smm/smm/store.py` explains the layout).

## Safety
- Nothing posts unless **all** hold: a named approval for that exact post; `AUTOMATION_ENABLED=true`; `SMM_ENABLED=true`;
  `SMM_MODE=approve`; the platform is in `SMM_LIVE_PLATFORMS`; `SMM_DRY_RUN=false`; the platform's tokens are set.
  Otherwise an approved post goes to Telegram at its time with its picture and exact words, for a person to post by hand.
- A post more than 20 hours late is not posted (the team is told). 3 failed tries on a platform: stop and alert.
- Code never deletes a live post. Tokens live only in GitHub secrets. Every action writes a row to `log/actions.jsonl`.

## Going live (in this order)
1. **Merge the pull request** (scheduled runs use the main branch) and push the `smm-content` branch.
2. **Telegram**: add variable `SMM_TELEGRAM_CHAT_ID` (the team chat); secret `DTJ_TELEGRAM_BOT_TOKEN` already exists for the
   brand intake. From now on, approved posts arrive in Telegram daily for posting by hand (shadow, Harsh's plan: 2 weeks).
3. **Instagram + Facebook** (needs a person, about an hour):
   - DTJ's Instagram is a Business account linked to DTJ's Facebook Page; put the audit link in the Instagram bio.
   - In Meta for Developers, a Business app with Facebook Login for Business; permissions `pages_show_list`,
     `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`.
     For DTJ's own accounts the app's admins can use it without App Review [VERIFY on the first test].
   - Make a long-lived Page access token; save secrets `META_PAGE_TOKEN`, `META_PAGE_ID`, `META_IG_USER_ID`.
   - `WP_USER` / `WP_APP_PASSWORD` (the SEO engine's WordPress Editor) are needed too: Meta fetches pictures from a public link,
     so each approved picture is uploaded to DTJ's WordPress media library at posting time.
4. **Test once**: Actions > "SMM daily" > Run (post) with a test post approved for a few minutes ahead, `SMM_LIVE_PLATFORMS=facebook`,
   `SMM_MODE=approve`, `SMM_DRY_RUN=false`, `SMM_ENABLED=true`, `AUTOMATION_ENABLED=true`. Check the post, then Instagram.
   Harsh's yes is needed for each of these switches (they make code post publicly).
5. **LinkedIn**: request the Community Management API for a new LinkedIn app (vetted; development tier first). Then secrets
   `LINKEDIN_TOKEN` (60 days), `LINKEDIN_ORG_ID`, variable `LINKEDIN_TOKEN_EXPIRES` (the run warns 10 days before).
6. **YouTube**: a Google Cloud project with the YouTube Data API, OAuth app "In production" (testing apps lose the refresh token
   in 7 days); secrets `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`. Only video posts go there.
7. **X**: a developer account with pay-per-use credits; OAuth 1.0a keys of DTJ's account: `X_API_KEY`, `X_API_SECRET`,
   `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`. About $0.20 a post with a link [X pricing page, 20 Oct 2026].

## Platform facts (checked 20 Oct 2026 on the official docs)
| Platform | Facts the code relies on | Source |
|---|---|---|
| Instagram | Graph API v26.0; container (`/media`) then `media_publish`; check `status_code` FINISHED; carousel up to 20; JPEG only, 8 MB, ratio 4:5 to 1.91:1; caption 2200, 30 hashtags; media from a public URL; ~50 API posts a day; `is_ai_generated`; insights `views, reach, likes, comments, saved, shares, total_interactions` | developers.facebook.com/docs/instagram-platform/content-publishing, /reference/ig-user/media, /reference/instagram-media/insights |
| Facebook Page | `/photos` (url + caption), multi-photo via unpublished photos + `attached_media`, `/feed`, reels via `/video_reels` start-upload-finish (3-90 s, 30 a day); insights `post_media_view`, `post_total_media_view_unique`, `post_clicks` (post_impressions deprecated) | developers.facebook.com/docs/pages-api/posts, /video-api/guides/reels-publishing, /graph-api/reference/v26.0/insights |
| LinkedIn | `POST /rest/posts`, `LinkedIn-Version: 202610`; images via `/rest/images?action=initializeUpload`; multi-image post; "little" text needs `\|{}@[]()<>#\*_~` escaped; `w_organization_social` via the vetted Community Management API; token 60 days | learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api |
| YouTube | resumable `videos.insert`; vertical video ≤ 3 min is a Short; title 100, description 5000 bytes; `containsSyntheticMedia`; Google's pages disagree on whether unaudited projects' uploads are forced private, so the run reports the privacy it got | developers.google.com/youtube/v3/docs/videos/insert, support.google.com/youtube/answer/7300965 |
| X | `POST /2/tweets`, `/2/media/upload` (v2); 4 pictures or 1 video; 280 characters (links count 23); `made_with_ai`; pay per use | docs.x.com/x-api/posts/create-post, /x-api/getting-started/pricing |

## Open (Harsh)
- D1: one yes for the whole week vs per post. Built: a named yes per post, but one command can name several (`p1-p7`).
- The Meta ads report picture (`public/images/results/meta-ads-dashboard.webp`) has round-number rows; not used until confirmed.
- May client brands be named on social? Week 2026-W44 names five (as the website does); it waits for the yes.
- Telegram buttons for the yes (in the bot) come after the SEO Telegram branch is merged (the bot workflow is shared).
