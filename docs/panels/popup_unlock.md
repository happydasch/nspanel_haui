# Popup Unlock Panel

```yaml
key: popup_unlock
type: popup_unlock
```

The unlock popup panel is being used internally to provide a unlocking mechanism for panels.

To use this panel, just set a unlock code to any other panel. The argument needs to be a string.

## Config

```yaml
panels:
  # this panel will be locked and can be unlocked using the unlock code
  - type: grid
    title: Unlock Panel
    unlock_code: "1234"
```
