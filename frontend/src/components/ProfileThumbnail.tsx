import { useEffect, useState } from "react";

export function ProfileThumbnail({ url, kind, name, className = "" }: { url?: string | null; kind?: string; name: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);
  return url && kind !== "system_fallback" && !failed
    ? <img src={url} alt="" className={`editor-card-thumb ${className}`} onError={() => setFailed(true)} />
    : <div className={`editor-card-thumb editor-card-thumb-fallback ${className}`} role="img" aria-label={name} title={name}><span>{name}</span></div>;
}
