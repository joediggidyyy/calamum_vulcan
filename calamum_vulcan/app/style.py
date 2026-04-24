"""Shared style tokens for the Calamum Vulcan Qt shell."""

from __future__ import annotations

from typing import Dict


COLOR_TOKENS = {
  'background': '#0a0d12',
  'surface': '#10161f',
  'surface_alt': '#141c27',
  'surface_card': '#16212d',
  'surface_soft': '#0f1722',
  'line': '#263546',
  'line_soft': '#32485f',
  'text': '#edf2f7',
  'muted': '#9aa9bc',
  'neutral': '#6b7b90',
  'info': '#4d91d6',
  'success': '#4fc08d',
  'warning': '#f3a948',
  'danger': '#e25757',
  'brand': '#3dd5f3',
  'brand_soft': '#1ca7c7',
}  # type: Dict[str, str]


def _scaled(value: int, scale: float) -> int:
  """Return a scaled pixel value with a sensible lower bound."""

  return max(1, int(round(value * scale)))


def tone_color(tone: str) -> str:
  """Return the accent color associated with a UI tone."""

  return COLOR_TOKENS.get(tone, COLOR_TOKENS['neutral'])


def panel_style(tone: str, selector: str = 'panel-frame', scale: float = 1.0) -> str:
  """Return a stylesheet string for one dashboard panel."""

  accent = tone_color(tone)
  return (
    'QFrame#{selector} {{'
    'background-color: {surface};'
    'border: 1px solid {line};'
    'border-left: 4px solid {accent};'
    'border-radius: {radius}px;'
    '}}'
    'QFrame#{selector} QLabel {{color: {text}; background: transparent; border: none;}}'
  ).format(
    selector=selector,
    surface=COLOR_TOKENS['surface'],
    line=COLOR_TOKENS['line'],
    accent=accent,
    radius=_scaled(16, scale),
    text=COLOR_TOKENS['text'],
  )


def pill_style(tone: str, selector: str = 'status-pill', scale: float = 1.0) -> str:
  """Return a stylesheet string for a header status pill."""

  accent = tone_color(tone)
  return (
    'QFrame#{selector} {{'
    'background-color: {surface};'
    'border: 1px solid {accent};'
    'border-radius: {radius}px;'
    '}}'
    'QFrame#{selector} QLabel {{color: {text}; background: transparent; border: none;}}'
  ).format(
    selector=selector,
    surface=COLOR_TOKENS['surface_alt'],
    accent=accent,
    radius=_scaled(14, scale),
    text=COLOR_TOKENS['text'],
  )


def metric_style(tone: str, selector: str = 'metric-block', scale: float = 1.0) -> str:
  """Return a softer card style for metric blocks."""

  accent = tone_color(tone)
  return (
    'QFrame#{selector} {{'
    'background-color: {surface};'
    'border: 1px solid {line};'
    'border-radius: {radius}px;'
    '}}'
    'QFrame#{selector} QLabel {{color: {text}; background: transparent; border: none;}}'
    'QFrame#{selector}:hover {{border-color: {accent};}}'
  ).format(
    selector=selector,
    surface=COLOR_TOKENS['surface_card'],
    line=COLOR_TOKENS['line_soft'],
    radius=_scaled(12, scale),
    text=COLOR_TOKENS['text'],
    accent=accent,
  )


def brand_frame_style(selector: str = 'brand-mark', scale: float = 1.0) -> str:
  """Return the style for brand surfaces."""

  return (
    'QFrame#{selector} {{'
    'background-color: {surface};'
    'border: 1px solid {line};'
    'border-radius: {radius}px;'
    '}}'
    'QFrame#{selector} QLabel {{color: {text}; background: transparent; border: none;}}'
  ).format(
    selector=selector,
    surface=COLOR_TOKENS['surface_soft'],
    line=COLOR_TOKENS['line_soft'],
    radius=_scaled(18, scale),
    text=COLOR_TOKENS['text'],
  )


def action_button_style(emphasis: str, enabled: bool, scale: float = 1.0) -> str:
  """Return the stylesheet string for a control-deck button."""

  text = COLOR_TOKENS['text'] if enabled else COLOR_TOKENS['muted']
  if emphasis == 'danger':
    accent = COLOR_TOKENS['danger']
  elif emphasis == 'warning':
    accent = COLOR_TOKENS['warning']
  elif emphasis == 'primary':
    accent = COLOR_TOKENS['info']
  elif emphasis == 'next':
    accent = COLOR_TOKENS['success']
    if enabled:
      text = COLOR_TOKENS['success']
  elif emphasis == 'next_warning':
    accent = COLOR_TOKENS['warning']
    if enabled:
      text = COLOR_TOKENS['success']
  elif emphasis == 'next_danger':
    accent = COLOR_TOKENS['danger']
    if enabled:
      text = COLOR_TOKENS['success']
  else:
    accent = COLOR_TOKENS['line']

  background = COLOR_TOKENS['surface_alt']
  hover_background = COLOR_TOKENS['surface_card']
  if not enabled:
    accent = COLOR_TOKENS['line']

  return (
    'QPushButton {{'
    'background-color: {background};'
    'color: {text};'
    'border: 1px solid {accent};'
    'border-radius: {radius}px;'
    'padding: {padding_y}px {padding_x}px;'
    'text-align: left;'
    'font-weight: 600;'
    'font-size: {font_size}px;'
    'min-height: {min_height}px;'
    '}}'
    'QPushButton:hover {{border-color: {hover}; background-color: {hover_background};}}'
  ).format(
    background=background,
    text=text,
    accent=accent,
    hover=accent,
    radius=_scaled(12, scale),
    padding_y=_scaled(12, scale),
    padding_x=_scaled(14, scale),
    font_size=_scaled(14, scale),
    min_height=_scaled(48, scale),
    hover_background=hover_background,
  )


def control_hint_style(scale: float = 1.0) -> str:
  """Return the style for control-deck hint labels."""

  return (
    'color: {muted}; font-size: {font_size}px; line-height: 1.35;'.format(
      muted=COLOR_TOKENS['muted'],
      font_size=_scaled(13, scale),
    )
  )


def detail_row_style(
  selector: str = 'panel-detail-row',
  scale: float = 1.0,
) -> str:
  """Return the style for structured panel detail rows."""

  return (
    'QFrame#{selector} {{'
    'background-color: {surface};'
    'border: 1px solid {line};'
    'border-radius: {radius}px;'
    '}}'
    'QFrame#{selector} QLabel {{background: transparent; border: none;}}'
  ).format(
    selector=selector,
    surface=COLOR_TOKENS['surface_soft'],
    line=COLOR_TOKENS['line_soft'],
    radius=_scaled(10, scale),
  )


def detail_key_style(scale: float = 1.0) -> str:
  """Return the style for structured panel detail keys."""

  return (
    'color: {muted}; font-size: {font_size}px; font-weight: 800; '
    'letter-spacing: 0.9px; '
    'font-family: Consolas, "Cascadia Mono", monospace;'
  ).format(
    muted=COLOR_TOKENS['muted'],
    font_size=_scaled(11, scale),
  )


def detail_value_style(scale: float = 1.0) -> str:
  """Return the style for structured panel detail values."""

  return (
    'color: {text}; font-size: {font_size}px; font-weight: 600; '
    'line-height: 1.35;'
  ).format(
    text=COLOR_TOKENS['text'],
    font_size=_scaled(14, scale),
  )


def mono_terminal_style(scale: float = 1.0) -> str:
  """Return the style for the operational log widget."""

  return (
    'QPlainTextEdit {'
    'background-color: #05070b;'
    'color: #dce4ee;'
    'border: 1px solid ' + COLOR_TOKENS['line_soft'] + ';'
    'border-radius: ' + str(_scaled(12, scale)) + 'px;'
    'padding: ' + str(_scaled(12, scale)) + 'px;'
    'font-family: Consolas, "Cascadia Mono", monospace;'
    'font-size: ' + str(_scaled(13, scale)) + 'px;'
    '}'
  )


WINDOW_STYLE = (
  'QMainWindow {background-color: ' + COLOR_TOKENS['background'] + ';}'
  'QWidget {background-color: transparent; color: ' + COLOR_TOKENS['text'] + ';}'
)