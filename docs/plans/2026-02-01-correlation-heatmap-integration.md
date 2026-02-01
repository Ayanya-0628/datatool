# Correlation Heatmap Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate the Correlation Heatmap feature into the existing web application workflow, ensuring the UI/UX for variable selection is consistent with other analysis modules (ANOVA, PCA, Cluster) by using the Sidebar and Modal.

**Architecture:**
- **Frontend:** Move Heatmap configuration from the content area to the shared "Variable Selection Modal". Update the Sidebar to trigger analysis. Use the main content area only for displaying results (Preview + Download).
- **Backend:** Reuse existing `app.py` endpoints `/api/analyze_heatmap` and `/api/export_heatmap_image`.

**Tech Stack:** JavaScript (Frontend), Flask (Backend), Matplotlib (Plotting)

---

### Task 1: Update Frontend State & Modal Logic

**Files:**
- Modify: `static/app.js`

**Step 1: Update State Definition**
- Add `heatmapX` and `heatmapY` arrays to the global `state` object.
- Add corresponding fields to `tempState`.

**Step 2: Update `updateUIForMethod`**
- Change logic to **SHOW** `dom.variableSection` and `dom.actionSection` when `state.analysisType === 'heatmap'`.
- Update `updateSidebarSummary` to display counts for X and Y variables when in heatmap mode.

**Step 3: Update `initVariableModal` & `openVariableModal`**
- In `openVariableModal`: Initialize `tempState.heatmapX` and `tempState.heatmapY`. Set modal title for Heatmap.
- In `renderMiddleActions`: Add buttons "Add to X Axis >" and "Add to Y Axis >" when type is heatmap.
- In `renderTargetPanels`: Add panels for "X Axis Variables" and "Y Axis Variables".
- In `confirmVariableChanges`: Save temp state to global state.

### Task 2: Integrate Analysis Trigger

**Files:**
- Modify: `static/app.js`

**Step 1: Unify Analysis Entry Point**
- Modify `runAnalysis()` function:
  - Add a case for `type === 'heatmap'`.
  - Validate that `state.heatmapX` and `state.heatmapY` are not empty.
  - Construct payload using state variables.
  - Call the backend API (`/api/analyze_heatmap`).
  - Handle the response to display the result (Preview Image).

**Step 2: Update Result Rendering**
- Ensure the result shows in the main area.
- Reuse `dom.heatmapResult` container but ensure it is displayed correctly by `runAnalysis`.
- Hide the "Configuration Card" logic (since we moved it to modal).

### Task 3: HTML Cleanup & Download Feature

**Files:**
- Modify: `templates/dashboard.html`

**Step 1: Remove Inline Configuration**
- Delete the `<div class="card mb-4">` inside `#heatmap-section` that contains the inline `<select>` elements for X/Y vars.
- Keep `#heatmap-result` for displaying the preview and download buttons.

**Step 2: Verify Download Buttons**
- Ensure the download buttons (`.btn-download-heatmap`) pass the correct parameters (format, 600 DPI) to `/api/export_heatmap_image`.
- (The existing backend logic supports `dpi` param, need to ensure frontend sends it).

### Task 4: Backend Verification (Quick Check)

**Files:**
- Check: `app.py`

**Step 1: Verify DPI handling**
- Confirm `/api/export_heatmap_image` accepts `dpi` parameter and passes it to `generate_heatmap_image`. (Checked: It does).

**Step 2: Verify Analysis Endpoint**
- Confirm `/api/analyze_heatmap` returns the base64 image for preview. (Checked: It does).

---
