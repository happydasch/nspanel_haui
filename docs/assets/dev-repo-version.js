(() => {
  const canonical = document.querySelector("link[rel='canonical']");
  if (!canonical) return;

  const siteBase = new URL("./", canonical.href);
  if (!siteBase.pathname.endsWith("/dev/")) return;

  const sources = Array.from(document.querySelectorAll(".md-source[data-md-component='source']"));
  if (!sources.length) return;

  let version = null;

  const updateFacts = () => {
    if (!version) return;
    for (const source of sources) {
      const fact = source.querySelector(".md-source__fact--version");
      if (!fact || fact.textContent === version) continue;
      fact.textContent = version;
    }
  };

  // The theme adds the source facts asynchronously and shows the latest stable
  // release, so observe each source only until its version fact exists. Writing
  // textContent from inside the observer re-fires it even for the same string,
  // which leaves the page in an endless microtask loop, so disconnect first.
  const watch = (source) => {
    if (source.querySelector(".md-source__fact--version")) {
      updateFacts();
      return;
    }
    const observer = new MutationObserver(() => {
      if (!source.querySelector(".md-source__fact--version")) return;
      observer.disconnect();
      updateFacts();
    });
    observer.observe(source, { childList: true, subtree: true });
  };

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
      sources.forEach(watch);
    })
    .catch((error) => console.error("Could not update the dev docs version badge", error));
})();
