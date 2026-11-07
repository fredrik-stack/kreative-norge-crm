export function EditorIcon({ name }: { name: "actors" | "people" | "import" | "export" | "map" | "admin" | "logout" }) {
  const paths = {
    actors: <><path d="M5 21V3h14v18M3 21h18M10 21v-5h4v5"/><path d="M9 7h.01M15 7h.01M9 11h.01M15 11h.01"/></>,
    people: <><circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/></>,
    import: <><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></>,
    export: <><path d="M12 3v13m-5-5 5 5 5-5M4 16v5h16v-5"/></>,
    map: <><path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Zm6-2v16m6-14v16"/></>,
    admin: <><path d="m9 3-1 3-3 1-2 5 2 5 3 1 1 3h6l1-3 3-1 2-5-2-5-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/></>,
    logout: <><path d="M9 4H4v16h5m5-13 5 5-5 5m-6-5h12"/></>,
  };
  return <svg className="editor-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
