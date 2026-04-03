import { useEffect, useState } from "react";
import { ApiError, createExportJob, getExportJob, getExportJobs, type ExportJobCreatePayload } from "../api";
import type { ExportJob } from "../types";


export function useExportJobs(tenantId: number | null) {
  const [jobs, setJobs] = useState<ExportJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [selectedJob, setSelectedJob] = useState<ExportJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  async function refreshJobs(nextSelectedJobId?: number | null) {
    if (!tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getExportJobs(tenantId);
      setJobs(data);
      const nextId = nextSelectedJobId ?? selectedJobId;
      const resolved = nextId && data.some((job) => job.id === nextId) ? nextId : data[0]?.id ?? null;
      setSelectedJobId(resolved);
      setForbidden(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) setForbidden(true);
      setError(err instanceof Error ? err.message : "Kunne ikke laste eksportjobber.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshSelectedJob(nextJobId?: number | null) {
    if (!tenantId) return;
    const targetId = nextJobId ?? selectedJobId;
    if (!targetId) {
      setSelectedJob(null);
      return;
    }
    try {
      const data = await getExportJob(tenantId, targetId);
      setSelectedJob(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke laste eksportjobb.");
    }
  }

  useEffect(() => {
    if (!tenantId) {
      setJobs([]);
      setSelectedJobId(null);
      setSelectedJob(null);
      return;
    }
    void refreshJobs();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  useEffect(() => {
    if (!tenantId || !selectedJobId) {
      setSelectedJob(null);
      return;
    }
    void refreshSelectedJob();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, selectedJobId]);

  async function createJob(payload: ExportJobCreatePayload) {
    if (!tenantId) return null;
    setBusy(true);
    setError(null);
    try {
      const created = await createExportJob(tenantId, payload);
      await refreshJobs(created.id);
      await refreshSelectedJob(created.id);
      return created;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke opprette eksportjobb.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  return {
    jobs,
    selectedJobId,
    setSelectedJobId,
    selectedJob,
    loading,
    busy,
    error,
    forbidden,
    refreshJobs,
    createJob,
  };
}
