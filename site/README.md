# Mod download

Download: https://abbvdidkxhdrzapvbidf.supabase.co/functions/v1/gore-hardmode-download

The link asks for a username and password. The zip is in a private Supabase bucket; `download-function.ts` checks the login and makes a link that lasts two minutes. Change the login in Supabase Edge Function secrets: `DOWNLOAD_USER` and `DOWNLOAD_PASS`.

Run `node site/build.mjs` to build the zip in `site/public/`. It doesn't update the live download automatically; upload the new zip to the bucket under the same name. The live zip was built from `fc65d0f` (SHA-256 `3391db790ecb8500122d82be646c96574b3fe69080d75a5c2d26b1d8c7c443bf`).

The Vercel download page in this folder isn't live. Its project uses `site` as the root, `node build.mjs` as the build command and `public` as the output. Vercel needs repo access before it can be deployed.
