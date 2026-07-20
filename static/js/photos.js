(() => {
  const dialog = document.getElementById("photo-lightbox");
  if (!dialog) return;

  const items = [...document.querySelectorAll("[data-photo-open]")];
  if (!items.length) return;

  const img = dialog.querySelector("[data-photo-img]");
  const title = dialog.querySelector("[data-photo-title]");
  const taken = dialog.querySelector("[data-photo-taken]");
  const location = dialog.querySelector("[data-photo-location]");
  const locationRow = dialog.querySelector("[data-photo-location-row]");
  const caption = dialog.querySelector("[data-photo-caption]");
  const captionRow = dialog.querySelector("[data-photo-caption-row]");
  const tags = dialog.querySelector("[data-photo-tags]");

  let index = 0;

  const read = (el) => ({
    src: el.dataset.src || "",
    title: el.dataset.title || "",
    location: el.dataset.location || "",
    taken: el.dataset.taken || "",
    caption: el.dataset.caption || "",
    tags: (el.dataset.tags || "")
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean),
  });

  const render = () => {
    const el = items[index];
    if (!el) return;
    const data = read(el);
    img.src = data.src;
    img.alt = data.title;
    title.textContent = data.title;
    taken.textContent = data.taken ? `拍摄于 ${data.taken}` : "";
    location.textContent = data.location || "";
    locationRow.hidden = !data.location;
    caption.textContent = data.caption || "";
    captionRow.hidden = !data.caption;
    tags.innerHTML = "";
    data.tags.forEach((tag) => {
      const span = document.createElement("span");
      span.className = "photo-lightbox__tag";
      span.textContent = tag;
      tags.appendChild(span);
    });
  };

  const openAt = (i) => {
    index = (i + items.length) % items.length;
    render();
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  };

  const close = () => {
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  };

  items.forEach((el, i) => {
    el.addEventListener("click", () => openAt(i));
  });

  dialog.querySelectorAll("[data-photo-close]").forEach((btn) => {
    btn.addEventListener("click", close);
  });
  dialog.querySelector("[data-photo-prev]")?.addEventListener("click", () => openAt(index - 1));
  dialog.querySelector("[data-photo-next]")?.addEventListener("click", () => openAt(index + 1));

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) close();
  });

  window.addEventListener("keydown", (event) => {
    if (!dialog.open) return;
    if (event.key === "Escape") close();
    if (event.key === "ArrowLeft") openAt(index - 1);
    if (event.key === "ArrowRight") openAt(index + 1);
  });
})();
