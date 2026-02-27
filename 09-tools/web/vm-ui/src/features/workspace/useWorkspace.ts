import { useEffect, useState } from "react";
import { fetchJson, postJson } from "../../api/client";
import { mapTimelineResponse } from "./adapters";

export type WorkflowProfile = {
  mode: string;
  description: string;
};

export type WorkflowRun = {
  run_id: string;
  status: string;
  requested_mode: string;
  request_text?: string;
  created_at?: string;
};

export type TimelineEvent = {
  event_id: string;
  event_type: string;
  created_at: string;
  payload: any;
};

export type PrimaryArtifact = {
  stageDir: string;
  artifactPath: string;
  content: string;
};

type ArtifactListingResponse = {
  stages?: Array<{ stage_dir: string; artifacts?: Array<string | { path?: string; filename?: string }> }>;
};

export function buildStartRunPayload(input: { mode: string; requestText: string }) {
  return { mode: input.mode, request_text: input.requestText.trim() };
}

export function useWorkspace(activeThreadId: string | null, activeRunId: string | null) {
  const [profiles, setProfiles] = useState<WorkflowProfile[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [runDetail, setRunDetail] = useState<any>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [primaryArtifact, setPrimaryArtifact] = useState<PrimaryArtifact | null>(null);
  const [artifactsByRun, setArtifactsByRun] = useState<Record<string, PrimaryArtifact | null>>({});
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingRunDetail, setLoadingRunDetail] = useState(false);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [loadingPrimaryArtifact, setLoadingPrimaryArtifact] = useState(false);

  const fetchProfiles = async () => {
    setLoadingProfiles(true);
    try {
      const data = await fetchJson<{ profiles: WorkflowProfile[] }>("/api/v2/workflow-profiles");
      setProfiles(data.profiles || []);
    } catch (e) {
      console.error("Failed to fetch profiles", e);
    } finally {
      setLoadingProfiles(false);
    }
  };

  const fetchRuns = async () => {
    if (!activeThreadId) {
      setRuns([]);
      return;
    }
    setLoadingRuns(true);
    try {
      const data = await fetchJson<{ runs: WorkflowRun[] }>(`/api/v2/threads/${activeThreadId}/workflow-runs`);
      setRuns(data.runs || []);
    } catch (e) {
      console.error("Failed to fetch runs", e);
    } finally {
      setLoadingRuns(false);
    }
  };

  const fetchRunDetail = async () => {
    if (!activeRunId) {
      setRunDetail(null);
      return;
    }
    setLoadingRunDetail(true);
    try {
      const data = await fetchJson<any>(`/api/v2/workflow-runs/${activeRunId}`);
      setRunDetail(data);
    } catch (e) {
      console.error("Failed to fetch run detail", e);
    } finally {
      setLoadingRunDetail(false);
    }
  };

  const fetchTimeline = async () => {
    if (!activeThreadId) {
      setTimeline([]);
      return;
    }
    setLoadingTimeline(true);
    try {
      const data = await fetchJson<unknown>(`/api/v2/threads/${activeThreadId}/timeline`);
      setTimeline(mapTimelineResponse(data));
    } catch (e) {
      console.error("Failed to fetch timeline", e);
    } finally {
      setLoadingTimeline(false);
    }
  };

  const fetchPrimaryArtifactForRun = async (runId: string): Promise<PrimaryArtifact | null> => {
    try {
      const listing = await fetchJson<ArtifactListingResponse>(
        `/api/v2/workflow-runs/${runId}/artifacts`
      );
      const stages = Array.isArray(listing.stages) ? listing.stages : [];
      let targetStage: string | null = null;
      let targetPath: string | null = null;
      for (const stage of stages) {
        const artifacts = Array.isArray(stage.artifacts) ? stage.artifacts : [];
        if (artifacts.length === 0) continue;
        const first = artifacts[0];
        const path = typeof first === "string" ? first : first.path || first.filename || null;
        if (path) {
          targetStage = stage.stage_dir;
          targetPath = path;
          break;
        }
      }
      if (!targetStage || !targetPath) {
        return null;
      }
      const contentPayload = await fetchJson<{ content?: string }>(
        `/api/v2/workflow-runs/${runId}/artifact-content?stage_dir=${encodeURIComponent(targetStage)}&artifact_path=${encodeURIComponent(targetPath)}`
      );
      return {
        stageDir: targetStage,
        artifactPath: targetPath,
        content: String(contentPayload.content ?? ""),
      };
    } catch (e) {
      console.error("Failed to fetch artifact", e);
      return null;
    }
  };

  const loadArtifactForRun = async (runId: string): Promise<PrimaryArtifact | null> => {
    if (!runId) return null;
    if (Object.prototype.hasOwnProperty.call(artifactsByRun, runId)) {
      return artifactsByRun[runId] ?? null;
    }
    const loaded = await fetchPrimaryArtifactForRun(runId);
    setArtifactsByRun((current) => ({ ...current, [runId]: loaded }));
    return loaded;
  };

  const fetchPrimaryArtifact = async () => {
    if (!activeRunId) {
      setPrimaryArtifact(null);
      return;
    }
    setLoadingPrimaryArtifact(true);
    const loaded = await fetchPrimaryArtifactForRun(activeRunId);
    setPrimaryArtifact(loaded);
    setArtifactsByRun((current) => ({ ...current, [activeRunId]: loaded }));
    setLoadingPrimaryArtifact(false);
  };

  const startRun = async (input: { mode: string; requestText: string }) => {
    if (!activeThreadId) return;
    try {
      await postJson(`/api/v2/threads/${activeThreadId}/workflow-runs`, buildStartRunPayload(input), "run");
      fetchRuns();
      fetchTimeline();
    } catch (e) {
      console.error("Failed to start run", e);
    }
  };

  const resumeRun = async () => {
    if (!activeRunId) return;
    try {
      await postJson(`/api/v2/workflow-runs/${activeRunId}/resume`, {}, "resume");
      fetchRunDetail();
      fetchRuns();
      fetchTimeline();
    } catch (e) {
      console.error("Failed to resume run", e);
    }
  };

  useEffect(() => {
    fetchProfiles();
  }, []);

  useEffect(() => {
    fetchRuns();
    fetchTimeline();
  }, [activeThreadId]);

  useEffect(() => {
    fetchRunDetail();
    fetchPrimaryArtifact();
  }, [activeRunId]);

  useEffect(() => {
    if (!activeThreadId) return;
    const timer = window.setInterval(() => {
      fetchRuns();
      fetchTimeline();
      if (activeRunId) fetchRunDetail();
    }, 4000);
    return () => window.clearInterval(timer);
  }, [activeThreadId, activeRunId]);

  return {
    profiles,
    runs,
    runDetail,
    timeline,
    primaryArtifact,
    artifactsByRun,
    loadingProfiles,
    loadingRuns,
    loadingRunDetail,
    loadingTimeline,
    loadingPrimaryArtifact,
    startRun,
    resumeRun,
    loadArtifactForRun,
    refreshRuns: fetchRuns,
    refreshTimeline: fetchTimeline,
    refreshPrimaryArtifact: fetchPrimaryArtifact,
  };
}
