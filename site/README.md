# mod download

download: https://abbvdidkxhdrzapvbidf.supabase.co/functions/v1/gore-hardmode-download

the link asks for a username and password. the zip is in a private Supabase bucket and `download-function.ts` checks the login and makes a link that lasts two minutes. change the login in Supabase Edge Function secrets: `DOWNLOAD_USER` and `DOWNLOAD_PASS`

run `node site/build.mjs` to build the zip in `site/public/`. it doesn't update the live download so upload the new zip to the bucket under the same name. the live zip was built from `fc65d0f` (SHA-256 `3391db790ecb8500122d82be646c96574b3fe69080d75a5c2d26b1d8c7c443bf`)

the Vercel download page in this folder isn't live. the project uses `site` as the root, `node build.mjs` as the build command and `public` as the output. Vercel needs repo access before it can be deployed
