# Hero Visual Asset

This placeholder is intentionally minimal.

**Replace with a custom premium visual asset:**
- Figma export (SVG/PNG/WebP)
- Rive animation (.riv via `@rive-app/canvas`)
- Lottie animation (.json via lottie-player)
- WebM/MP4 video loop (`<video autoplay muted loop playsinline>`)

**Do NOT hand-code complex human illustration in SVG/CSS here.**
The cosmic background is handled entirely by CSS in `style.css` (`.cosmic-hero` block).

**How to use the placeholder:**
Add to `landing/index.html` inside `.hero-content`:
```html
<!-- Replace this placeholder with a custom Figma/Rive/Lottie/WebM asset later. -->
<div class="hero-visual" aria-hidden="true">
  <img src="/assets/hero/hero-visual-placeholder.svg" alt="" width="400" height="300" />
</div>
```

Then add CSS:
```css
.hero-visual { opacity: 0.5; pointer-events: none; }
```
