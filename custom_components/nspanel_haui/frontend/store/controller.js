// @ts-check
/**
 * NSPanel HAUI - Lit reactive controller for the editor store.
 *
 * Subscribes the host element to the store while it is connected, so any
 * action that commits state re-renders the shell.
 */
export class StoreController {
  /**
   * @param {{ requestUpdate: () => void }} host
   * @param {{ subscribe: (listener: (state: any, previous: any) => void) => () => void }} store
   * @param {(state: any) => void} [onChange]
   */
  constructor(host, store, onChange) {
    this.host = host;
    this.store = store;
    this.onChange = onChange;
    /** @type {(() => void)|null} */
    this._unsubscribe = null;
  }

  hostConnected() {
    this._unsubscribe = this.store.subscribe((state) => {
      this.onChange?.(state);
      this.host.requestUpdate();
    });
  }

  hostDisconnected() {
    this._unsubscribe?.();
    this._unsubscribe = null;
  }
}
