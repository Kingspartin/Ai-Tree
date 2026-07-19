# 🛡️ Offline Privacy Toolkit

A single-file, 100% offline toolkit that runs from a **USB stick** in any browser — **phone or PC**.
No install, no server, no internet, no dependencies.

**Three tools in one page:**

| Tool | What it does |
|------|--------------|
| 🔍 **Metadata Viewer** | Reads hidden metadata inside images — EXIF, **GPS location**, camera make/model/serial, timestamps, XMP, IPTC, PNG text chunks — and flags the privacy-sensitive fields. A button opens the GPS location in an online map. |
| 🌐 **Reverse Search launcher** | Opens the image on external reverse-image engines (Google Lens, Yandex, Bing, TinEye) to find where it appears online and its source. A "show all results" toggle turns off each engine's safe-search / content filter. Direct links for image URLs; clipboard-copy + upload flow for local files. |
| 🧽 **Metadata Eraser** | Strips all that metadata out. *Lossless* mode keeps the original pixels (JPEG/PNG); *Re-encode* mode redraws the image for a guaranteed-clean file of any format. Batch-capable. |
| 🔥 **Secure Shredder** | Overwrites the actual bytes of files **you pick** with multiple passes, then blanks them to 0 bytes so you can delete an empty shell. |

Plus a **separate file, [`trash-bin.html`](trash-bin.html)** — a Secure Trash Bin that collects files into a
list and, on *Empty Bin*, securely overwrites and blanks them all at once.

Everything happens in your browser's memory. Nothing is uploaded — turn on Airplane Mode and it all still works.

---

## 📦 Put it on a USB

Copy **[`privacy-toolkit.html`](privacy-toolkit.html)** and **[`trash-bin.html`](trash-bin.html)** to the root of a USB drive
(keep them in the same folder so the in-app link works). Open `privacy-toolkit.html` to start.

- **Windows / macOS / Linux** — plug in, double-click `privacy-toolkit.html`.
- **Android** — plug the USB in via OTG, open the Files app, tap `privacy-toolkit.html` → *Open with* a browser.
- **iPhone / iPad** — use a Lightning/USB-C reader, open Files, tap the file (opens in Safari).

---

## 🔬 Honest limits (please read)

- **The viewer & eraser** work on any browser, fully offline.
- **The Reverse Search launcher** only *opens* external engines in new tabs — it runs no searches itself and
  sends nothing on its own; the toolkit stays offline until you tap an engine button, and those third-party
  sites need internet. "Show all results" just flips each engine's own safe-search parameter (the same toggle
  in their settings). Tip: reverse-search a *cleaned* copy if you don't want an engine to also receive the
  photo's EXIF/GPS.
- **The Trash Bin (`trash-bin.html`)** uses the same in-place overwrite as the shredder; it needs Chrome/Edge
  on desktop or Android.
- **The shredder** uses the browser **File System Access API** to overwrite files in place. That API exists on
  **Chrome / Edge (desktop & Android)**. On **iOS Safari and Firefox** it's unavailable — the page detects this
  and shows OS-level alternatives (`shred -u` on Linux, etc.) instead of pretending to work.
- **Wiping on USB sticks & SSDs isn't 100% guaranteed.** These drives sometimes save your "overwrite" to a
  different spot and quietly keep the original, so scraps can survive. Overwriting still helps, but the real
  fix is to **encrypt the whole drive** (BitLocker To Go, VeraCrypt, or LUKS) — then any leftovers are just
  unreadable gibberish. On old spinning hard drives, overwriting works fine.

No warranty. For high-stakes data, combine this with full-disk encryption — and, for maximum assurance,
physical destruction of the media.

---

## 🧱 How it's built

Pure vanilla HTML/CSS/JavaScript in one file — no frameworks, no CDN, no network calls. The EXIF/TIFF, JPEG,
and PNG parsers and the lossless metadata strippers are hand-written and run entirely client-side, which is
what makes the whole thing work from a USB with no internet.
