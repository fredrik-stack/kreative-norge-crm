import { useEffect } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useNavigate, useParams } from "react-router-dom";

export function useRouteSyncedSelection(options: {
  routeParam: string;
  basePath: string;
  selectedId: number | "new" | null;
  setSelectedId: Dispatch<SetStateAction<number | "new" | null>>;
  syncWhenParamMissing?: boolean;
}) {
  const { routeParam, basePath, selectedId, setSelectedId, syncWhenParamMissing = true } = options;
  const navigate = useNavigate();
  const params = useParams();
  const paramValue = params[routeParam];

  useEffect(() => {
    if (!paramValue) return;
    if (paramValue === "new") {
      setSelectedId((current) => (current === "new" ? current : "new"));
      return;
    }
    const parsed = Number(paramValue);
    if (!Number.isNaN(parsed)) {
      setSelectedId((current) => (current === parsed ? current : parsed));
    }
  }, [paramValue, setSelectedId]);

  useEffect(() => {
    const target =
      selectedId === "new"
        ? `${basePath}/new`
        : typeof selectedId === "number"
          ? `${basePath}/${selectedId}`
          : null;
    if (!target) return;
    if (!paramValue && !syncWhenParamMissing) return;
    const current = paramValue ? `${basePath}/${paramValue}` : null;
    if (current !== target) {
      navigate(target, { replace: true });
    }
  }, [basePath, navigate, paramValue, selectedId, syncWhenParamMissing]);

  return { navigate, paramValue };
}
