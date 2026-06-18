"""Nature-style plotting helpers for SlyLab.

This module adapts the local SLY/nature-skills Python plotting lane into a
small JSON-friendly API layer.
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PALETTE = {
    "blue_main": "#0F4D92",
    "green_3": "#8BCF8B",
    "red_strong": "#B64342",
    "neutral_light": "#CFCECE",
    "neutral_mid": "#767676",
    "teal": "#42949E",
    "violet": "#9A4D8E",
}

PALETTES = {
    "nature": [
        PALETTE["blue_main"],
        PALETTE["green_3"],
        PALETTE["red_strong"],
        PALETTE["teal"],
        PALETTE["violet"],
        PALETTE["neutral_light"],
    ],
    "nmi_pastel": ["#484878", "#7884B4", "#B4C0E4", "#E4CCD8", "#F0C0CC", "#E4E4F0"],
    "clinical": ["#272727", "#E28E2C", "#D24B40", "#5B8FD6", "#7BAA5B", "#C45AD6"],
    "material": ["#77D7D1", "#33B5A5", "#B9A7E8", "#7C6CCF", "#E53935", "#D9D9D9"],
}


def apply_nature_style(font_size: float = 7, axes_linewidth: float = 0.8) -> None:
    """Apply Nature-style matplotlib defaults."""
    plt.rcParams["font.family"] = "sans-serif"
    # 英文优先 Arial/Helvetica，中文字符按顺序回退到 Noto CJK / 微软雅黑 / SimHei，避免豆腐块
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei", "DejaVu Sans", "Liberation Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["font.size"] = font_size
    plt.rcParams["axes.linewidth"] = axes_linewidth
    plt.rcParams["axes.grid"] = False
    plt.rcParams["axes.spines.right"] = True
    plt.rcParams["axes.spines.top"] = True
    plt.rcParams["xtick.top"] = True
    plt.rcParams["ytick.right"] = True
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"
    plt.rcParams["legend.frameon"] = False


def _palette(name: str | None, n: int) -> list[str]:
    colors = PALETTES.get(name or "nature", PALETTES["nature"])
    return (colors * ((n // len(colors)) + 1))[:n]


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        raise ValueError(f"列不存在: {column}")
    series = pd.to_numeric(df[column], errors="coerce")
    if series.notna().sum() == 0:
        raise ValueError(f"列没有有效数值: {column}")
    return series


def _encode_figure(fig, fmt: str = "png", dpi: int = 300) -> dict:
    fmt = (fmt or "png").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    if fmt not in {"png", "svg", "pdf", "tiff", "jpeg"}:
        raise ValueError("format 仅支持 png/svg/pdf/tiff/jpeg")

    fig.tight_layout(pad=1.2)
    buffer = BytesIO()
    fig.savefig(buffer, format=fmt, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    raw = buffer.getvalue()
    result = {"data": base64.b64encode(raw).decode("utf-8"), "format": fmt}
    if fmt == "svg":
        result["editable_text"] = "<text" in raw.decode("utf-8", errors="ignore")
    return result


def add_panel_label(ax, label: str = "a", x: float = -0.08, y: float = 1.05) -> None:
    ax.text(x, y, label, transform=ax.transAxes, fontsize=14, fontweight="bold", ha="left", va="bottom")


def draw_grouped_bar(df: pd.DataFrame, config: dict) -> dict:
    category_col = config.get("category_col")
    value_cols = config.get("value_cols") or []
    if not category_col or category_col not in df.columns:
        raise ValueError("grouped_bar 需要有效的 category_col")
    if not value_cols:
        raise ValueError("grouped_bar 需要 value_cols")

    categories = df[category_col].astype(str).tolist()
    values = [_numeric_series(df, col).to_numpy() for col in value_cols]
    errors = None
    error_cols = config.get("error_cols") or []
    if error_cols:
        if len(error_cols) != len(value_cols):
            raise ValueError("error_cols 数量必须与 value_cols 一致")
        errors = [_numeric_series(df, col).to_numpy() for col in error_cols]

    apply_nature_style(config.get("font_size", 7))
    fig, ax = plt.subplots(figsize=(float(config.get("width", 7.2)), float(config.get("height", 4.2))))
    colors = _palette(config.get("palette"), len(value_cols))
    x = np.arange(len(categories))
    width = 0.78 / len(value_cols)
    labels = config.get("labels") or value_cols

    for i, (series, label, color) in enumerate(zip(values, labels, colors)):
        offset = (i - (len(value_cols) - 1) / 2) * width
        err = None if errors is None else errors[i]
        ax.bar(
            x + offset,
            series,
            width=width,
            label=label,
            color=color,
            edgecolor="black",
            linewidth=1.0,
            yerr=err,
            capsize=3 if err is not None else 0,
            error_kw={"elinewidth": 1.1, "capthick": 1.1},
        )

    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=float(config.get("x_rotation", 0)), ha="center")
    ax.set_ylabel(config.get("ylabel") or "Value")
    if config.get("xlabel"):
        ax.set_xlabel(config["xlabel"])
    if config.get("title"):
        ax.set_title(config["title"], fontsize=config.get("font_size", 7) + 1)
    if len(value_cols) > 1:
        ax.legend(fontsize=config.get("font_size", 7), loc=config.get("legend_loc", "best"))
    if config.get("panel_label"):
        add_panel_label(ax, str(config["panel_label"]))
    return _encode_figure(fig, config.get("format", "png"), int(config.get("dpi", 300)))


def draw_trend(df: pd.DataFrame, config: dict) -> dict:
    x_col = config.get("x_col")
    y_cols = config.get("y_cols") or []
    if not x_col or x_col not in df.columns:
        raise ValueError("trend 需要有效的 x_col")
    if not y_cols:
        raise ValueError("trend 需要 y_cols")

    x_raw = df[x_col]
    x_numeric = pd.to_numeric(x_raw, errors="coerce")
    x = np.arange(len(x_raw)) if x_numeric.isna().any() else x_numeric.to_numpy()

    apply_nature_style(config.get("font_size", 7))
    fig, ax = plt.subplots(figsize=(float(config.get("width", 7.2)), float(config.get("height", 4.2))))
    colors = _palette(config.get("palette"), len(y_cols))
    labels = config.get("labels") or y_cols
    for y_col, label, color in zip(y_cols, labels, colors):
        ax.plot(x, _numeric_series(df, y_col).to_numpy(), marker="o", ms=4, lw=2.0, color=color, label=label)
    if x_numeric.isna().any():
        ax.set_xticks(x)
        ax.set_xticklabels(x_raw.astype(str).tolist(), rotation=float(config.get("x_rotation", 0)))
    ax.set_xlabel(config.get("xlabel") or x_col)
    ax.set_ylabel(config.get("ylabel") or "Value")
    if config.get("title"):
        ax.set_title(config["title"], fontsize=config.get("font_size", 7) + 1)
    if len(y_cols) > 1:
        ax.legend(fontsize=config.get("font_size", 7), loc=config.get("legend_loc", "best"))
    if config.get("panel_label"):
        add_panel_label(ax, str(config["panel_label"]))
    return _encode_figure(fig, config.get("format", "png"), int(config.get("dpi", 300)))


def draw_heatmap(df: pd.DataFrame, config: dict) -> dict:
    value_cols = config.get("value_cols") or []
    if not value_cols:
        raise ValueError("heatmap 需要 value_cols")
    matrix = np.column_stack([_numeric_series(df, col).to_numpy() for col in value_cols])
    row_label_col = config.get("row_label_col")
    row_labels = df[row_label_col].astype(str).tolist() if row_label_col in df.columns else None

    apply_nature_style(config.get("font_size", 7))
    fig, ax = plt.subplots(figsize=(float(config.get("width", 6.2)), float(config.get("height", 4.8))))
    im = ax.imshow(matrix, cmap=config.get("cmap", "magma"), aspect="auto")
    cbar = fig.colorbar(im, ax=ax)
    if config.get("cbar_label"):
        cbar.set_label(config["cbar_label"])
    ax.set_xticks(range(len(value_cols)))
    ax.set_xticklabels(value_cols, rotation=30, ha="right")
    if row_labels:
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)
    if config.get("annotate", False):
        norm = plt.Normalize(vmin=float(np.nanmin(matrix)), vmax=float(np.nanmax(matrix)))
        cmap_obj = plt.get_cmap(config.get("cmap", "magma"))
        for (i, j), val in np.ndenumerate(matrix):
            r, g, b, _ = cmap_obj(norm(val))
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color="white" if lum < 0.5 else "black")
    if config.get("panel_label"):
        add_panel_label(ax, str(config["panel_label"]))
    return _encode_figure(fig, config.get("format", "png"), int(config.get("dpi", 300)))


def draw_forest(df: pd.DataFrame, config: dict) -> dict:
    label_col = config.get("label_col")
    estimate_col = config.get("estimate_col")
    ci_low_col = config.get("ci_low_col")
    ci_high_col = config.get("ci_high_col")
    required = [label_col, estimate_col, ci_low_col, ci_high_col]
    if not all(col and col in df.columns for col in required):
        raise ValueError("forest 需要 label_col/estimate_col/ci_low_col/ci_high_col")

    labels = df[label_col].astype(str).tolist()
    est = _numeric_series(df, estimate_col).to_numpy()
    low = _numeric_series(df, ci_low_col).to_numpy()
    high = _numeric_series(df, ci_high_col).to_numpy()

    apply_nature_style(config.get("font_size", 7))
    fig, ax = plt.subplots(figsize=(float(config.get("width", 5.2)), float(config.get("height", 3.6))))
    colors = _palette(config.get("palette"), len(labels))
    y = np.arange(len(labels))[::-1]
    for yi, value, lo, hi, color in zip(y, est, low, high, colors):
        ax.plot([lo, hi], [yi, yi], color=color, lw=1.6)
        ax.plot(value, yi, marker="o", ms=5, color=color)
    ax.axvline(float(config.get("ref", 0)), color=PALETTE["neutral_mid"], linestyle="--", linewidth=1.1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(config.get("xlabel") or "Effect size")
    if config.get("title"):
        ax.set_title(config["title"], fontsize=config.get("font_size", 7) + 1)
    if config.get("panel_label"):
        add_panel_label(ax, str(config["panel_label"]))
    return _encode_figure(fig, config.get("format", "png"), int(config.get("dpi", 300)))


def generate_nature_plot(df: pd.DataFrame, chart_type: str, config: dict | None = None) -> dict:
    """Generate a Nature-style figure from a DataFrame and JSON config."""
    config = config or {}
    chart_type = (chart_type or "").lower()
    if chart_type == "grouped_bar":
        return draw_grouped_bar(df, config)
    if chart_type == "trend":
        return draw_trend(df, config)
    if chart_type == "heatmap":
        return draw_heatmap(df, config)
    if chart_type == "forest":
        return draw_forest(df, config)
    raise ValueError("chart_type 仅支持 grouped_bar/trend/heatmap/forest")
