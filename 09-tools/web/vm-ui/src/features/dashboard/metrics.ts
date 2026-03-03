/**
 * Dashboard metrics utilities
 */

export interface MetricCard {
  label: string;
  value: number | string;
  change?: number;
  trend?: "up" | "down" | "neutral";
  icon?: string;
}

export interface ActivityItem {
  id: string;
  type: "brand" | "project" | "thread" | "run";
  name: string;
  action: string;
  timestamp: string;
}

export interface OnboardingMetrics {
  total_started: number;
  total_completed: number;
  completion_rate: number;
  average_time_to_first_value_ms: number;
  dropoff_by_step: Record<string, number>;
}

/**
 * Format milliseconds to human readable duration
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  const minutes = Math.round(ms / 60000);
  return `${minutes}m`;
}

/**
 * Format percentage with 1 decimal place
 */
export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Calculate trend based on current and previous values
 */
export function calculateTrend(
  current: number,
  previous: number
): { trend: "up" | "down" | "neutral"; change: number } {
  if (previous === 0) return { trend: "neutral", change: 0 };
  const change = ((current - previous) / previous) * 100;
  return {
    trend: change > 0 ? "up" : change < 0 ? "down" : "neutral",
    change: Math.abs(change),
  };
}

/**
 * Mock activity data for dashboard
 * In production, this would come from an API endpoint
 */
export function getRecentActivity(): ActivityItem[] {
  return [
    {
      id: "1",
      type: "run",
      name: "Blog Post Workflow",
      action: "completed",
      timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    },
    {
      id: "2",
      type: "thread",
      name: "Campaign Q1",
      action: "created",
      timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    },
    {
      id: "3",
      type: "project",
      name: "Marketing Digital",
      action: "updated",
      timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    },
    {
      id: "4",
      type: "brand",
      name: "Acme Corp",
      action: "created",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    },
  ];
}

/**
 * Format relative time
 */
export function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
