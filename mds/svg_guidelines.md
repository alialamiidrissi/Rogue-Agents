# SVG Generation Guidelines for PNG Conversion

To ensure high-quality visual outputs when converting SVGs to PNGs for the comic template, follow these guidelines:

## 1. Canvas and ViewBox
- **Standard Aspect Ratio**: Create SVGs with a standardized aspect ratio (e.g., 500x1000 or 1:2) to ensure predictable scaling.
- **Vertical Orientation**: Since characters are standing, a vertical canvas is preferred.
- **Padding**: Leave `10%` padding around the character to avoid cropping when placed in panels.

## 2. Line Work and Style
- **Stroke Width**: Use a minimum stroke width of `3px` to ensure lines remain visible after downscaling.
- **Contrast**: High contrast colors work best. Avoid creating subtle gradients as they may band during format conversion.
- **Complexity**: Keep shapes simple ("Paper Doll" style) to match the comic aesthetic.

## 3. Transparency
- **Background**: The SVG background MUST be transparent. Do not include a solid rectangle background layer.
- **Format**: Ensure the conversion pipeline supports Alpha channels (RGBA).

## 4. Size Recommendations
- **Source SVG**: Defined with vector paths (infinite resolution).
- **Target PNG**: recommended resolution of `1000px` height.
    - Low Res (Preview): `500px` height.
    - High Res (Production): `2000px` height.

## 5. Usage in Template
- The template expects PNGs.
- `<img>` tags will handle the scaling (CSS `height: 80%`).
- Ensure the character's feet are near the bottom of the SVG viewbox to align correctly with the ground level in the CSS.
