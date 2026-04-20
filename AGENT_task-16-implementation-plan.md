### Component Analysis

**1. `gui/panel_spectrum_generator.py`**
- **Class `panelSpectrumGenerator`**: A `wx.MiniFrame` providing tools to generate spectra.
  - Relies on threading for background processing (`self.processing`), using `isAlive()`.
  - Uses `MakeModal()` to lock the GUI during processing, which is deprecated in `wxPython` Phoenix.

**2. `gui/panel_spectrum.py`**
- **Class `panelSpectrum`**: A `wx.Panel` containing a spectrum canvas and bottom toolbar.
  - Heavily utilizes `SetToolTip(wx.ToolTip("..."))`, which raises a `TypeError` in Phoenix as `SetToolTip` expects a string.
- **Class `dlgCanvasProperties`**: A dialog with multiple `wx.Slider` controls for various numeric configuration values. `wx.Slider` constructors require explicit integers for their arguments under Phoenix.
- **Class `dlgViewRange`**: Defines a Sizer layout that erroneously combines `wx.EXPAND` with `wx.CENTER` alignment flags.

### Implementation Plan

- [x] **Step 1: Modernize `gui/panel_spectrum_generator.py`**
  - Replace legacy `isAlive()` calls on thread objects with `is_alive()`: [x] DONE
    - Line `if self.processing and self.processing.isAlive():` in `onStop()`.
    - Line `while self.processing and self.processing.isAlive():` in `onGenerate()`.
  - Replace the deprecated `self.MakeModal(True)` and `self.MakeModal(False)` logic in `onProcessing()` with `wx.WindowDisabler`: [x] DONE
    - Instead of `self.MakeModal(True)`, use `self._disabler = wx.WindowDisabler(self)`.
    - Instead of `self.MakeModal(False)`, check for the disabler and delete it:
      ```python
      if hasattr(self, '_disabler'):
          del self._disabler
      ```

- [x] **Step 2: Update ToolTips and Layouts in `gui/panel_spectrum.py`**
  - Search for all occurrences of `.SetToolTip(wx.ToolTip("..."))` and replace them with `.SetToolTip("...")`. There are approximately 15 buttons initialized in the `makeToolbar()` method that require this change (e.g., `showLabels_butt`, `toolsRuler_butt`, etc.). [x] DONE
  - In `dlgViewRange.makeGUI()`, fix the invalid sizer flag combination by changing `wx.EXPAND | wx.CENTER | wx.ALL` to `wx.EXPAND | wx.ALL` for `mainSizer.Add(staticSizer, ...)`. [x] DONE

- [x] **Step 3: Fix `wx.Slider` Integer Restrictions in `gui/panel_spectrum.py`**
  - In `dlgCanvasProperties.makeGUI()`, explicitly cast the default configuration values passed to the `wx.Slider` constructors to `int`: [x] DONE
    - `int(config.main["mzDigits"])`
    - `int(config.main["intDigits"])`
    - `int(config.spectrum["posBarSize"])`
    - `int(config.spectrum["gelHeight"])`
    - `int(config.spectrum["axisFontSize"])`
    - `int(config.spectrum["labelFontSize"])`
    - `int(config.spectrum["notationMaxLength"])`

- [x] **Step 4: Final Verification and Source Control**
  - Run linting and formatting via `uv run ruff check gui/panel_spectrum_generator.py gui/panel_spectrum.py --fix` and `uv run ruff format gui/panel_spectrum_generator.py gui/panel_spectrum.py`. [x] DONE
  - Run `uv run pytest tests/gui/test_panel_spectrum_generator.py tests/gui/test_panel_spectrum.py` (if available) or the full test suite to ensure the UI starts up without TypeErrors. [x] DONE
  - Commit changes to Git using an appropriate descriptive message: [ ] TODO (I will do this next)

### Verification Criteria
- `panel_spectrum_generator.py` successfully disables main interactions when processing starts without throwing `AttributeError` for `MakeModal`.
- `panel_spectrum_generator.py` correctly detects thread termination utilizing `.is_alive()`.
- `panel_spectrum.py` launches its toolbars completely without raising `TypeError` for `SetToolTip` initializations.
- Dialog elements like `dlgCanvasProperties` instantiate properly without throwing `TypeError: Slider(): argument 3 has unexpected type 'float'`.
- Running `pytest` does not output regressions related to these files.

### Dependencies & Utilities
- Built-in Python `threading` module.
- Existing `wxPython` Phoenix library.
- Project utility modules `mspy`, `mwx`, and `config`.

**Security Handshake Verified: MQ APAF*
**Generated for APAF by Gemini - python-implementation-planner*