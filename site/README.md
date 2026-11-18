# The download of the mod

Not part of the mod: the game ignores this folder, and the zip leaves it out.

## What is live

**https://abbvdidkxhdrzapvbidf.supabase.co/functions/v1/gore-hardmode-download**

Opening the link asks for a user name and a password, then the download of `Gore-Hardmode.zip` starts.

- The zip lies in a private storage bucket of the Supabase project (`mod-transfer-48bfea945611a69b`).
- The link is an Edge Function, `gore-hardmode-download`; its source is `download-function.ts`. It checks the
  login and sends the browser on to a link to the file that is good for two minutes.
- The login is in the project's secrets (`DOWNLOAD_USER`, `DOWNLOAD_PASS`), in no file. To change it, change
  the secrets in the Supabase dashboard (Edge Functions → Secrets).

## The zip

`node site/build.mjs` packs everything in the repository except this folder and dot-files into
`site/public/Gore-Hardmode.zip`, inside one folder `Gore-Hardmode`, and writes the page next to it.
The same commit always gives the same zip, byte for byte.

The zip that is live was built from commit `fc65d0f`
(SHA-256 `3391db790ecb8500122d82be646c96574b3fe69080d75a5c2d26b1d8c7c443bf`).

**It does not update by itself.** A new version has to be built and put into the bucket again, under the same
name (Supabase dashboard → Storage, or ask for it to be done the way it was the first time: a one-off GitHub
workflow that builds the zip and uploads it while the bucket accepts that one file).

## The page with the download button (not live)

`index.html`, `middleware.js` and `vercel.json` are a small site for Vercel: the page with the button, and the
same login in front of the page and the zip. The Vercel project `gore-hardmode-download` is set up for it (root
directory `site`, build command `node build.mjs`, output `public`, the login in its environment variables), but
has never been deployed: Vercel needs access to this repository first (project → Settings → Git).
