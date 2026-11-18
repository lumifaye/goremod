# Mod download

This folder isn't part of the mod and isn't included in the zip.

## Live download

**https://abbvdidkxhdrzapvbidf.supabase.co/functions/v1/gore-hardmode-download**

The link asks for a username and password, then downloads `Gore-Hardmode.zip`.

- The zip is in a private Supabase storage bucket in `mod-transfer-48bfea945611a69b`.
- `download-function.ts` is the `gore-hardmode-download` Edge Function. It checks the login and redirects to a file link that expires after two minutes.
- The login is in the project secrets, not in a file. To change it, update `DOWNLOAD_USER` and `DOWNLOAD_PASS` in Supabase under Edge Functions → Secrets.

## Building the zip

Run `node site/build.mjs`. It puts `Gore-Hardmode.zip` and the page in `site/public/`. The zip has one `Gore-Hardmode` folder. It leaves out dot-files, `site`, `fork`, `release`, `dist`, `node_modules`, `Untitled.png`, and the `WiiU`, `PC`, `VR` and `Android` source folders. The same commit gives the same zip, byte for byte.

The live zip was built from commit `fc65d0f` (SHA-256 `3391db790ecb8500122d82be646c96574b3fe69080d75a5c2d26b1d8c7c443bf`).

**It doesn't update itself.** Build a new zip and upload it to the bucket under the same name in Supabase Storage, or use the same one-off GitHub workflow used the first time.

## Download page (not live)

`index.html`, `middleware.js` and `vercel.json` are the Vercel page, download button and login. The `gore-hardmode-download` Vercel project is set up with `site` as the root, `node build.mjs` as the build command, `public` as the output and the login in its environment variables. It hasn't been deployed; Vercel needs access to this repository first (project → Settings → Git).
