(() => {
  const nodes = [...document.querySelectorAll("pre.mermaid")];
  if (!nodes.length || typeof mermaid === "undefined") return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    securityLevel: "strict",
    fontFamily: '"Manrope", "PingFang SC", "Noto Sans SC", sans-serif',
    themeVariables: {
      darkMode: true,
      background: "#121C2E",
      primaryColor: "#182338",
      primaryTextColor: "#F4EDE3",
      primaryBorderColor: "rgba(244, 237, 227, 0.18)",
      secondaryColor: "#0B1424",
      secondaryTextColor: "#C4CBD6",
      tertiaryColor: "#070E18",
      tertiaryTextColor: "#8B97A8",
      lineColor: "#C4CBD6",
      textColor: "#F4EDE3",
      mainBkg: "#182338",
      nodeBorder: "rgba(244, 237, 227, 0.18)",
      clusterBkg: "#0B1424",
      titleColor: "#F4EDE3",
      edgeLabelBackground: "#121C2E",
      actorBkg: "#182338",
      actorTextColor: "#F4EDE3",
      signalColor: "#E8A35A",
      noteBkgColor: "#182338",
      noteTextColor: "#F4EDE3",
    },
    flowchart: {
      useMaxWidth: true,
      htmlLabels: true,
      curve: reducedMotion ? "linear" : "basis",
    },
    sequence: {
      useMaxWidth: true,
      mirrorActors: false,
    },
  });

  mermaid.run({ nodes }).catch((err) => {
    console.error("Mermaid render failed:", err);
    nodes.forEach((node) => {
      node.closest(".mermaid-block")?.classList.add("mermaid-block--error");
    });
  });
})();
