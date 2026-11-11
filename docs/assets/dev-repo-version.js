(() => {
  const source = document.querySelector(".md-source[data-md-component='source']");
  const canonical = document.querySelector("link[rel='canonical']");
  if (!source || !canonical) return;

  const siteBase = new URL("./", canonical.href);
  if (!siteBase.pathname.endsWith("/dev/")) return;

  let version = "dev";
  const updateVersion = () => {
    const fact = source.querySelector(".md-source__fact--version");
    if (fact) fact.textContent = version;
  };
  new MutationObserver(updateVersion).observe(source, { childList: true, subtree: true });
  updateVersion();

  const manifestUrl =
    "https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/custom_components/" +
    "nspanel_haui/manifest.json";
  fetch(manifestUrl)
    .then((response) => {
      if (!response.ok) throw new Error("Dev manifest could not be loaded");
      return response.json();
    })
    .then((data) => {
      if (typeof data.version !== "string" || !data.version) {
        throw new Error("Dev release version is missing");
      }
      version = data.version;
      updateVersion();
    })
    .catch((error) => console.error("Could not update the dev docs version badge", error));
})();
