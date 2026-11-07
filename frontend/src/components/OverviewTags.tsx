import { useLayoutEffect, useRef, useState } from "react";

/** Fit complete tags into the space left by the name and categories. */
export function OverviewTags({ tags, name, onOpen }: {
  tags: Array<{ id: number; name: string }>;
  name: string;
  onOpen: () => void;
}) {
  const areaRef = useRef<HTMLDivElement>(null);
  const probeRef = useRef<HTMLDivElement>(null);
  const [{ visible, firstMaxWidth }, setFit] = useState<{ visible: number; firstMaxWidth?: number }>({ visible: tags.length });
  useLayoutEffect(() => {
    const area = areaRef.current, probe = probeRef.current;
    if (!area || !probe) return;
    let cancelled = false;
    const measure = () => {
      if (cancelled) return;
      const width = area.clientWidth, height = area.clientHeight;
      if (!width || !height) return;
      const gap = parseFloat(getComputedStyle(area).gap) || 0;
      const sizes = Array.from(probe.querySelectorAll<HTMLElement>(".card-tag-probe")).map(el => el.getBoundingClientRect());
      const counter = probe.querySelector<HTMLElement>(".tag-count-probe")!;
      const fits = (count: number) => {
        const items = sizes.slice(0, count);
        if (count < tags.length) {
          counter.textContent = `+${tags.length - count}`;
          items.push(counter.getBoundingClientRect());
        }
        let x = 0, y = 0, rowHeight = 0;
        for (const item of items) {
          if (x > 0 && x + item.width > width + 0.5) { y += rowHeight + gap; x = 0; rowHeight = 0; }
          rowHeight = Math.max(rowHeight, item.height);
          if (y + rowHeight > height + 0.5) return false;
          x += item.width + gap;
        }
        return true;
      };
      let count = tags.length;
      while (count > 0 && !fits(count)) count--;
      let firstMaxWidth: number | undefined;
      if (count === 0 && tags.length > 1) {
        counter.textContent = `+${tags.length - 1}`;
        const available = width - counter.getBoundingClientRect().width - gap;
        if (available >= 24 && sizes[0].height <= height + 0.5) {
          count = 1;
          firstMaxWidth = available;
        }
      }
      setFit(current => current.visible === count && current.firstMaxWidth === firstMaxWidth ? current : { visible: count, firstMaxWidth });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(area);
    void document.fonts.ready.then(measure);
    return () => { cancelled = true; observer.disconnect(); };
  }, [tags]);
  if (!tags.length) return null;
  return <div className="card-tags" ref={areaRef}>
    {tags.slice(0, visible).map(tag => <span key={tag.id} className="mini-pill tag" style={firstMaxWidth ? { maxWidth: firstMaxWidth } : undefined} title={tag.name}>{tag.name}</span>)}
    {visible < tags.length ? <button type="button" className="tag-count" aria-label={`Vis ${tags.length - visible} flere tags for ${name}`} onClick={event => { event.stopPropagation(); onOpen(); }}>+{tags.length - visible}</button> : null}
    <div className="card-tags-probe" ref={probeRef} aria-hidden="true">
      {tags.map(tag => <span className="card-tag-probe" key={tag.id}>{tag.name}</span>)}<span className="tag-count-probe">+{tags.length}</span>
    </div>
  </div>;
}
