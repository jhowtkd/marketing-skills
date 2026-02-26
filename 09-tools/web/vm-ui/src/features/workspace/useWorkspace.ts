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

export function buildStartRunPayload(input: { mode: string; requestText: string }) {
  return { mode: input.mode, request_text: input.requestText.trim() };
}

export function useWorkspace(activeThreadId: string | null, activeRunId: string | null) {
  const [profiles, setProfiles] = useState<WorkflowProfile[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [runDetail, setRunDetail] = useState<any>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingRunDetail, setLoadingRunDetail] = useState(false);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

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
  }, [activeRunId]);

  return {
    profiles,
    runs,
    runDetail,
    timeline,
    loadingProfiles,
    loadingRuns,
    loadingRunDetail,
    loadingTimeline,
    startRun,
    resumeRun,
    refreshRuns: fetchRuns,
    refreshTimeline: fetchTimeline,
  };
}
