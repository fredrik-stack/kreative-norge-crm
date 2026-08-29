import type { MouseEventHandler, ReactNode } from "react";

type PhoneLinkProps = {
  value: string | null | undefined;
  dialUri: string | null | undefined;
  empty?: ReactNode;
  className?: string;
  onClick?: MouseEventHandler<HTMLElement>;
};

export function PhoneLink({ value, dialUri, empty = "—", className, onClick }: PhoneLinkProps) {
  if (!value) return <>{empty}</>;
  if (!dialUri) {
    return (
      <span className={className} onClick={onClick}>
        {value}
      </span>
    );
  }
  return (
    <a className={className} href={dialUri} onClick={onClick}>
      {value}
    </a>
  );
}
