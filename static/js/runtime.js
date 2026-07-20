(() => {
  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const block = btn.closest(".code-block");
      const code = block?.querySelector("code");
      if (!code) return;
      try {
        await navigator.clipboard.writeText(code.innerText);
        const prev = btn.textContent;
        btn.textContent = "已复制";
        setTimeout(() => {
          btn.textContent = prev || "复制";
        }, 1200);
      } catch {
        btn.textContent = "失败";
      }
    });
  });

  const progress = document.querySelector("[data-progress]");
  const body = document.querySelector("[data-article-body]");
  if (progress && body) {
    const update = () => {
      const rect = body.getBoundingClientRect();
      const total = body.offsetHeight - window.innerHeight;
      const scrolled = Math.min(Math.max(-rect.top, 0), Math.max(total, 1));
      const pct = total > 0 ? (scrolled / total) * 100 : 100;
      progress.style.width = `${pct}%`;
    };
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  const tocLinks = [...document.querySelectorAll(".toc__item")];
  if (tocLinks.length) {
    const headings = tocLinks
      .map((link) => document.querySelector(link.getAttribute("href")))
      .filter(Boolean);
    const onScroll = () => {
      let current = headings[0];
      for (const heading of headings) {
        if (heading.getBoundingClientRect().top <= 120) current = heading;
      }
      tocLinks.forEach((link) => {
        link.classList.toggle(
          "is-active",
          link.getAttribute("href") === `#${current.id}`,
        );
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }
})();
