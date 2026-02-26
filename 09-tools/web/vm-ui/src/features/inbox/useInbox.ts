import { useEffect, useState } from "react";
import { fetchJson, postJson } from "../../api/client";
import { mapTasksResponse, mapApprovalsResponse, Task, Approval } from "./adapters";

export type { Task, Approval } from "./adapters";

export type ArtifactItem = {
  path: string;
  [key: string]: any;
};

export type ArtifactStage = {
  stage_dir: string;
  artifacts?: string[] | ArtifactItem[];
  [key: string]: any;
};

export function useInbox(activeThreadId: string | null, activeRunId: string | null) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [artifactStages, setArtifactStages] = useState<ArtifactStage[]>([]);
  const [artifactContents, setArtifactContents] = useState<Record<string, string>>({});
  
  const fetchTasks = async () => {
    if (!activeThreadId) {
      setTasks([]);
      return;
    }
    try {
      const data = await fetchJson<unknown>(`/api/v2/threads/${activeThreadId}/tasks`);
      setTasks(mapTasksResponse(data));
    } catch (e) {
      console.error("Failed to fetch tasks", e);
    }
  };

  const fetchApprovals = async () => {
    if (!activeThreadId) {
      setApprovals([]);
      return;
    }
    try {
      const data = await fetchJson<unknown>(`/api/v2/threads/${activeThreadId}/approvals`);
      setApprovals(mapApprovalsResponse(data));
    } catch (e) {
      console.error("Failed to fetch approvals", e);
    }
  };

  const fetchArtifacts = async () => {
    if (!activeRunId) {
      setArtifactStages([]);
      return;
    }
    try {
      const data = await fetchJson<{ stages: ArtifactStage[] }>(`/api/v2/workflow-runs/${activeRunId}/artifacts`);
      setArtifactStages(data.stages || []);
    } catch (e) {
      console.error("Failed to fetch artifacts", e);
    }
  };

  const loadArtifactContent = async (stageDir: string, artifactPath: string) => {
    if (!activeRunId) return;
    const key = `${stageDir}/${artifactPath}`;
    try {
      const payload = await fetchJson<{ content?: string }>(
        `/api/v2/workflow-runs/${activeRunId}/artifact-content?stage_dir=${encodeURIComponent(stageDir)}&artifact_path=${encodeURIComponent(artifactPath)}`
      );
      setArtifactContents((prev) => ({ ...prev, [key]: String(payload.content ?? "") }));
    } catch (e) {
      console.error("Failed to fetch artifact content", e);
    }
  };

  const completeTask = async (taskId: string) => {
    try {
      await postJson(`/api/v2/tasks/${taskId}/complete`, {}, "complete-task");
      fetchTasks();
    } catch (e) {
      console.error("Failed to complete task", e);
    }
  };

  const commentTask = async (taskId: string, message: string) => {
    try {
      await postJson(`/api/v2/tasks/${taskId}/comment`, { message }, "comment-task");
      fetchTasks();
    } catch (e) {
      console.error("Failed to comment on task", e);
    }
  };

  const grantApproval = async (approvalId: string) => {
    try {
      await postJson(`/api/v2/approvals/${approvalId}/grant`, {}, "grant-approval");
      fetchApprovals();
    } catch (e) {
      console.error("Failed to grant approval", e);
    }
  };

  useEffect(() => {
    fetchTasks();
    fetchApprovals();
  }, [activeThreadId]);

  useEffect(() => {
    fetchArtifacts();
    setArtifactContents({});
  }, [activeRunId]);

  return {
    tasks,
    approvals,
    artifactStages,
    artifactContents,
    completeTask,
    commentTask,
    grantApproval,
    loadArtifactContent,
    refreshTasks: fetchTasks,
    refreshApprovals: fetchApprovals,
    refreshArtifacts: fetchArtifacts,
  };
}
