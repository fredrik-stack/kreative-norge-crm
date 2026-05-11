import { useEffect, useState } from "react";
import {
  ApiError,
  commitImportJob,
  createImportJob,
  generateImportJobAi,
  getImportJob,
  getImportJobs,
  getImportRows,
  previewImportJob,
  saveImportJobDecisions,
  uploadImportJobFile,
  type ImportDecisionPayload,
  type ImportJobCreatePayload,
  type ImportRowsQuery,
} from "../api";
import type { ImportJob, ImportRow, Paginated } from "../types";

export function useImportJobs(tenantId: number | null) {
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [selectedJob, setSelectedJob] = useState<ImportJob | null>(null);
  const [rowsPage, setRowsPage] = useState<Paginated<ImportRow> | null>(null);
  const [rowsQuery, setRowsQuery] = useState<ImportRowsQuery>({ page: 1 });
  const [loading, setLoading] = useState(false);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  async function refreshJobs(nextSelectedJobId?: number | null) {
    if (!tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getImportJobs(tenantId);
      setJobs(data);
      const preferredId = nextSelectedJobId ?? selectedJobId;
      const resolvedSelectedId = preferredId && data.some((job) => job.id === preferredId) ? preferredId : data[0]?.id ?? null;
      setSelectedJobId(resolvedSelectedId);
      setForbidden(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true);
      }
      setError(err instanceof Error ? err.message : "Kunne ikke laste importjobber.");
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
      const data = await getImportJob(tenantId, targetId);
      setSelectedJob(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke laste importjobben.");
    }
  }

  async function refreshRows(nextQuery?: ImportRowsQuery, nextJobId?: number | null) {
    if (!tenantId) return;
    const targetId = nextJobId ?? selectedJobId;
    if (!targetId) {
      setRowsPage(null);
      return;
    }
    setRowsLoading(true);
    try {
      const query = nextQuery ?? rowsQuery;
      const data = await getImportRows(tenantId, targetId, query);
      setRowsPage(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke laste importrader.");
    } finally {
      setRowsLoading(false);
    }
  }

  useEffect(() => {
    if (!tenantId) {
      setJobs([]);
      setSelectedJobId(null);
      setSelectedJob(null);
      setRowsPage(null);
      return;
    }
    void refreshJobs();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  useEffect(() => {
    if (!tenantId || !selectedJobId) {
      setSelectedJob(null);
      setRowsPage(null);
      return;
    }
    void refreshSelectedJob();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, selectedJobId]);

  useEffect(() => {
    if (!tenantId || !selectedJobId) {
      setRowsPage(null);
      return;
    }
    void refreshRows();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, selectedJobId, rowsQuery]);

  async function createJob(payload: ImportJobCreatePayload) {
    if (!tenantId) return null;
    setBusyAction("create");
    setError(null);
    try {
      const created = await createImportJob(tenantId, payload);
      await refreshJobs(created.id);
      await refreshSelectedJob(created.id);
      return created;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke opprette importjobb.");
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function uploadFile(file: File, jobId?: number) {
    if (!tenantId) return null;
    const targetJobId = jobId ?? selectedJobId;
    if (!targetJobId) return null;
    setBusyAction("upload");
    setError(null);
    try {
      const updated = await uploadImportJobFile(tenantId, targetJobId, file);
      setSelectedJob(updated);
      await refreshJobs(updated.id);
      await refreshSelectedJob(updated.id);
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke laste opp filen.");
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function runPreview(jobId?: number) {
    if (!tenantId) return null;
    const targetJobId = jobId ?? selectedJobId;
    if (!targetJobId) return null;
    setBusyAction("preview");
    setError(null);
    try {
      const updated = await previewImportJob(tenantId, targetJobId);
      setSelectedJob(updated);
      await refreshJobs(updated.id);
      await refreshSelectedJob(updated.id);
      await refreshRows({ ...rowsQuery, page: 1 }, updated.id);
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke kjøre preview.");
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function generateAi(retryFailed = false) {
    if (!tenantId || !selectedJobId) return null;
    setBusyAction("generate-ai");
    setError(null);
    try {
      const updated = await generateImportJobAi(tenantId, selectedJobId, {
        retry_failed: retryFailed,
        batch_size: 1,
      });
      setSelectedJob(updated);
      await refreshJobs(updated.id);
      await refreshSelectedJob(updated.id);
      await refreshRows(undefined, updated.id);
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke generere AI-forslag.");
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  useEffect(() => {
    if (!tenantId || !selectedJobId || !selectedJob) return;
    const aiStatus = String((selectedJob.summary_json ?? {}).ai_generation_status ?? "");
    if (!["pending", "running"].includes(aiStatus)) return;
    if (busyAction) return;
    const timer = window.setTimeout(() => {
      void generateAi(false);
    }, 2500);
    return () => window.clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, selectedJobId, selectedJob, busyAction]);

  async function saveDecisions(rows: ImportDecisionPayload[]) {
    if (!tenantId || !selectedJobId) return null;
    setBusyAction("decisions");
    setError(null);
    try {
      const result = await saveImportJobDecisions(tenantId, selectedJobId, rows);
      await refreshSelectedJob();
      await refreshRows();
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke lagre vurderinger.");
      throw err;
    } finally {
      setBusyAction(null);
    }
  }

  async function commit(skipUnresolved: boolean) {
    if (!tenantId || !selectedJobId) return null;
    setBusyAction("commit");
    setError(null);
    try {
      const updated = await commitImportJob(tenantId, selectedJobId, skipUnresolved);
      setSelectedJob(updated);
      await refreshJobs(updated.id);
      await refreshSelectedJob(updated.id);
      await refreshRows(undefined, updated.id);
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunne ikke committe importen.");
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  return {
    jobs,
    selectedJobId,
    setSelectedJobId,
    selectedJob,
    rowsPage,
    rowsQuery,
    setRowsQuery,
    loading,
    rowsLoading,
    busyAction,
    error,
    forbidden,
    refreshJobs,
    refreshRows,
    createJob,
    uploadFile,
    runPreview,
    generateAi,
    saveDecisions,
    commit,
  };
}
