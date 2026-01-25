---
name: slack-gif-creator
description: Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for Slack."
license: Complete terms in LICENSE.txt
---

# Slack GIF Creator

A toolkit providing utilities and knowledge for creating animated GIFs optimized for Slack.

## Slack Requirements

**Dimensions:**

- Emoji GIFs: 128x128 (recommended)
- Message GIFs: 480x480

**Parameters:**

- FPS: 10-30 (lower is smaller file size)
- Colors: 48-128 (fewer = smaller file size)
- Duration: Keep under 3 seconds for emoji GIFs

## Core Workflow

```python
from core.gif_builder import GIFBuilder
from PIL import Image, ImageDraw

# 1. Create builder
builder = GIFBuilder(width=128, height=128, fps=10)

# 2. Generate frames
for i in range(12):
    frame = Image.new('RGB', (128, 128), (240, 248, 255))
    draw = ImageDraw.Draw(frame)
    # Draw your animation using PIL primitives
    builder.add_frame(frame)

# 3. Save with optimization
builder.save('output.gif', num_colors=48, optimize_for_emoji=True)
```

## Drawing Graphics

### Drawing from Scratch

Use PIL ImageDraw primitives:

```python
from PIL import ImageDraw

draw = ImageDraw.Draw(frame)
draw.ellipse([x1, y1, x2, y2], fill=(r, g, b), outline=(r, g, b), width=3)
draw.polygon(points, fill=(r, g, b), outline=(r, g, b), width=3)
draw.line([(x1, y1), (x2, y2)], fill=(r, g, b), width=5)
draw.rectangle([x1, y1, x2, y2], fill=(r, g, b), outline=(r, g, b), width=3)
```

### Making Graphics Look Good

- **Use thicker lines** - Always set `width=2` or higher
- **Add visual depth**: Use gradients, layer multiple shapes
- **Pay attention to colors**: Use vibrant, complementary colors

## Animation Concepts

### Shake/Vibrate

Use `math.sin()` or `math.cos()` with frame index.

### Pulse/Heartbeat

Use `math.sin(t * frequency * 2 * math.pi)` for smooth pulse.

### Bounce

Use `interpolate()` with `easing='bounce_out'` for landing.

### Spin/Rotate

`image.rotate(angle, resample=Image.BICUBIC)`

### Fade In/Out

Create RGBA image, adjust alpha channel.

### Slide

Use `interpolate()` with `easing='ease_out'` for smooth stop.

## Optimization Strategies

1. **Fewer frames** - Lower FPS (10 instead of 20)
2. **Fewer colors** - `num_colors=48` instead of 128
3. **Smaller dimensions** - 128x128 instead of 480x480
4. **Remove duplicates** - `remove_duplicates=True` in save()

## Dependencies

```bash
pip install pillow imageio numpy
```
