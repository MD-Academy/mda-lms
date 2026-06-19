# Diploma artwork

The diploma is drawn by overlaying the student's name, issue date, and optional
final grade onto a full-page background image.

## To use your own diploma design

1. Export your diploma artwork as a **landscape** image and save it here as:

       mda-lms/backend/assets/diploma-bg.png

   (A4 landscape ratio, ~300 DPI looks best — e.g. 3508 × 2480 px. PNG or JPG.)

2. Ideally export it **without** the sample "STUDENT FULL NAME" line — the real
   name is drawn in that spot. If your artwork keeps the placeholder, leave
   `"mask": True` in `DIPLOMA_CONFIG` (in `diplomas.py`) and tune `mask_color`
   to match the parchment so the placeholder is painted over.

3. Fine-tune where the name / date / grade land by editing `DIPLOMA_CONFIG` at
   the top of `diplomas.py`. All positions are **fractions of the page**
   (0 = top/left, 1 = bottom/right), so they don't depend on the image size.

If `diploma-bg.png` is missing, a clean built-in vector certificate is used, so
the feature works either way.

`mda-logo.png` here is used on the recommendation-letter letterhead (and the
fallback certificate). Replace it to change the letterhead logo.
