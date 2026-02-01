# Correlation Heatmap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a customizable "Correlation Bubble Heatmap" feature in the web app, strictly following the visual style of `draw_combined_heatmap.py`, with high-resolution (600 DPI) and vector download options.

**Architecture:**
- **Backend**: New `modules/heatmap.py` to encapsulate matplotlib logic (using `Agg` backend). New API endpoints in `app.py` for generating previews and downloads.
- **Frontend**: Add new sidebar tab "相关性热图" in `dashboard.html` with X/Y variable selectors. Update `app.js` to handle interactions.
- **Style**: Replicate the "Blue-White-Red" colormap, bubble size logic, significance stars, and font settings from the reference script.

**Tech Stack:** Python (Matplotlib, SciPy, Pandas), Flask, JavaScript (Vanilla).

---

### Task 1: Create Heatmap Module

**Files:**
- Create: `modules/heatmap.py`

**Step 1: Create module with style constants**
Define colors, fonts, and the core plotting function `draw_heatmap(df, x_cols, y_cols, ax)` adapted from `draw_combined_heatmap.py`. Ensure it uses `matplotlib.use('Agg')` to prevent GUI errors.

**Step 2: Implement correlation calculation**
Port `calculate_correlations` and `get_star` functions. Ensure robust handling of NaNs and empty intersections.

**Step 3: Implement main generation function**
Create `generate_heatmap_image(df, x_cols, y_cols, format='png', dpi=300)` that:
1. Creates a figure.
2. Calls the drawing logic.
3. Saves to a `BytesIO` object.
4. Returns the buffer.

### Task 2: Backend API Implementation

**Files:**
- Modify: `app.py`

**Step 1: Import heatmap module**
Import the new module. Handle potential `ImportError` gracefully (though matplotlib is required).

**Step 2: Add Preview Endpoint**
Create `/api/analyze_heatmap` (POST):
- Input: `data_id`, `x_vars`, `y_vars`
- Logic: Fetch df, call `generate_heatmap_image` with DPI=100 (fast preview).
- Output: Base64 encoded image string.

**Step 3: Add Export Endpoint**
Create `/api/export_heatmap_image` (POST):
- Input: `data_id`, `x_vars`, `y_vars`, `format` (png/pdf/svg), `dpi` (default 600).
- Logic: Call `generate_heatmap_image` with high DPI.
- Output: File download stream.

### Task 3: Frontend UI (HTML)

**Files:**
- Modify: `templates/dashboard.html`

**Step 1: Add Sidebar Navigation**
Add a new link `<li><a href="#" data-target="heatmap-section">相关性热图</a></li>` in the sidebar.

**Step 2: Add Configuration Panel**
Add a new section `<div id="heatmap-section" class="content-section">`:
- Two multi-select boxes: "选择 X 轴变量" and "选择 Y 轴变量".
- "开始分析" (Analyze) button.

**Step 3: Add Result Display Area**
- Image container for the preview.
- Download buttons group: "下载 PNG (600 DPI)", "下载 PDF", "下载 SVG".

### Task 4: Frontend Logic (JS)

**Files:**
- Modify: `static/app.js`

**Step 1: Variable Initialization**
Update `updateVariableSelectors()` to populate the new X/Y selectors in the heatmap section when a file is uploaded.

**Step 2: Analysis Handler**
Bind click event to "Analyze" button:
- Collect selected X/Y vars.
- Call `/api/analyze_heatmap`.
- Display loading spinner.
- Render returned Base64 image.

**Step 3: Download Handler**
Bind click events to download buttons:
- Send POST request to `/api/export_heatmap_image` with specific format/DPI.
- Trigger browser download.

### Task 5: Verification

**Step 1: Test Calculation**
Verify R and P values match `scipy.stats.pearsonr` outputs.

**Step 2: Test Visualization**
- Check "Blue-White-Red" gradient.
- Check Bubble sizes (abs(R)).
- Check Significance stars (*, **, ***).
- Check Font consistency (Times New Roman).

**Step 3: Test Download**
- Verify downloaded PNG is 600 DPI.
- Verify PDF/SVG are vector graphics (text selectable).
