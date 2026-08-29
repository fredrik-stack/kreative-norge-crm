import type { MouseEventHandler, ReactNode } from "react";

type PhoneLinkProps = {
  value: string | null | undefined;
  dialUri: string | null | undefined;
  countryCallingCodeHint?: string | null;
  empty?: ReactNode;
  className?: string;
  onClick?: MouseEventHandler<HTMLElement>;
};

export function PhoneLink({
  value,
  dialUri,
  countryCallingCodeHint,
  empty = "—",
  className,
  onClick,
}: PhoneLinkProps) {
  if (!value) return <>{empty}</>;
  const visibleHint = value.trim().startsWith("+") ? null : countryCallingCodeHint;
  const content = (
    <>
      {value}
      {visibleHint ? <span className="phone-country-code-hint"> (+{visibleHint})</span> : null}
    </>
  );
  if (!dialUri) {
    return (
      <span className={className} onClick={onClick}>
        {content}
      </span>
    );
  }
  return (
    <a className={className} href={dialUri} onClick={onClick}>
      {content}
    </a>
  );
}
