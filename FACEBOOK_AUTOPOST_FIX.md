# Facebook Auto-Post Feed Fix

## What was happening

The auto poster uploaded images to `/{page_id}/photos`. When the follow-up `/{page_id}/feed` call failed, the old code published the photo directly to `/{page_id}/photos` and still returned success.

That can create the exact symptom where the image is visible in the Page Photos section, but no normal Page feed/posts item appears for other accounts.

## What changed

Image auto-posting now:

1. Uploads the image as unpublished with `published=false`.
2. Creates the actual Page feed post with `/{page_id}/feed`.
3. Attaches the uploaded photo using `attached_media[0]`.
4. Returns an error instead of silently publishing a Photos-only item if the feed post fails.

## Required Facebook token permissions

Use a Page access token for the same `FB_PAGE_ID` with at least:

```text
pages_manage_posts
pages_read_engagement
```

If GitHub Actions now fails with a Facebook permission error, regenerate the Page token with those permissions and update the `FB_PAGE_TOKEN` repository secret.

Optional: set `FB_GRAPH_VERSION` in GitHub Secrets or workflow env if you want to pin a specific version, for example `v24.0`.
