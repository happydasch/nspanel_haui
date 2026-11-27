---
title: Display Models
description: EU vs US NSPanel hardware, TFT layout selection and updates
---

# Display Models

The NSPanel exists in an EU and a US version. NSPanel HAUI needs to know how the panel is mounted, because the display uses a different layout per orientation.

## Which model do I have?

| Setting | Mounting | Layout |
|---------|----------|--------|
| **European (standard)** — default | Landscape | 480 × 320 |
| **US (portrait)** | Portrait | 320 × 480 |

A US panel mounted in landscape works like an EU panel and uses the default.

## Select the model

1. Open the device's **Settings**.
2. Under **General**, set **Display Model**.
3. Select **Save**. When updates are enabled, the editor asks whether to install the matching display file (TFT) now.

If you answer no, install it later with **Install** beside **Display** in the **Updates** sidebar. The display cannot report its layout, so the hub cannot detect a wrong one on its own.

The setting controls:

- **the editor**: every panel picture and the live preview use the selected layout
- **updates**: the landscape or portrait TFT is installed, whichever matches
- **gestures**: the screen edges follow the selected model

!!! note
    The firmware is the same for all models. Only the display file (TFT) differs, and every release includes both. Each model has exactly one: the 921600 bps display link is part of that file, so there is no high-speed or normal-speed version to pick.
