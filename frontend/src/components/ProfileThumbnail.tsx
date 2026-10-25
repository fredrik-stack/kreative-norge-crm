import { useEffect, useState } from "react";

export function ProfileThumbnail({ url, name, className = "" }: { url?: string | null; name: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);
  return url && !failed
    ? <img src={url} alt="" className={`editor-card-thumb ${className}`} onError={() => setFailed(true)} />
    : <div className={`editor-card-thumb editor-card-thumb-fallback ${className}`} aria-label="Ingen tilgjengelig bilde"><span aria-hidden="true">{name.slice(0, 2).toUpperCase()}</span></div>;
}
