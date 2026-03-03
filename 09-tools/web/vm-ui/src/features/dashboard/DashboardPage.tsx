import { useEffect, useState } from "react";
import { BrandApi } from "../../api/typed-client";
import { fetchJson } from "../../api/client";
import type { Brand } from "../../types/api";
import type { OnboardingMetrics, ActivityItem, MetricCard } from "./metrics";
import {
  formatDuration,
  formatPercentage,
  getRecentActivity,
  formatRelativeTime,
} from "./metrics";

interface DashboardStats {
  totalBrands: number;
  totalProjects: number;
  totalThreads: number;
  recentRuns: number;
}

export default function DashboardPage(): JSX.Element {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [onboardingMetrics, setOnboardingMetrics] =
    useState<OnboardingMetrics | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard(): Promise<void> {
      try {
        setLoading(true);
        setError(null);

        // Load brands to count stats
        const brandsResponse = await BrandApi.listBrands();
        const brands = Array.isArray(brandsResponse.brands)
          ? brandsResponse.brands
          : [];

        // Count projects and threads across all brands
        let totalProjects = 0;
        let totalThreads = 0;

        for (const brand of brands.slice(0, 5)) {
          // Limit to avoid too many requests
          try {
            const projectsResponse = await fetchJson<{
              projects: { project_id: string }[];
            }>(`/api/v2/projects?brand_id=${brand.brand_id}`);
            const projects = Array.isArray(projectsResponse.projects)
              ? projectsResponse.projects
              : [];
            totalProjects += projects.length;

            // Count threads for each project
            for (const project of projects.slice(0, 3)) {
              try {
                const threadsResponse = await fetchJson<{
                  threads: { thread_id: string }[];
                }>(`/api/v2/threads?project_id=${project.project_id}`);
                const threads = Array.isArray(threadsResponse.threads)
                  ? threadsResponse.threads
                  : [];
                totalThreads += threads.length;
              } catch {
                // Ignore errors for individual projects
              }
            }
          } catch {
            // Ignore errors for individual brands
          }
        }

        if (cancelled) return;

        setStats({
          totalBrands: brands.length,
          totalProjects,
          totalThreads,
          recentRuns: 0, // Would need a separate endpoint
        });

        // Load onboarding metrics
        try {
          const onboarding = await fetchJson<OnboardingMetrics>(
            "/api/v2/onboarding/metrics"
          );
          if (!cancelled) {
            setOnboardingMetrics(onboarding);
          }
        } catch {
          // Onboarding endpoint might not be available
        }

        // Load recent activity (mock for now)
        if (!cancelled) {
          setActivity(getRecentActivity());
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  const metrics: MetricCard[] = stats
    ? [
        {
          label: "Brands",
          value: stats.totalBrands,
          icon: "🏢",
        },
        {
          label: "Projects",
          value: stats.totalProjects,
          icon: "📁",
        },
        {
          label: "Threads",
          value: stats.totalThreads,
          icon: "💬",
        },
      ]
    : [];

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-primary"></div>
          <p className="text-slate-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="rounded-lg bg-red-50 p-6 text-center">
          <p className="mb-2 text-red-600">Error loading dashboard</p>
          <p className="text-sm text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-6">
      <header className="mb-8">
        <h1 className="font-serif text-2xl font-bold text-slate-900">
          Dashboard
        </h1>
        <p className="mt-1 text-slate-600">
          Overview of your marketing workspace
        </p>
      </header>

      {/* Metrics Grid */}
      <section className="mb-8">
        <h2 className="mb-4 font-serif text-lg font-semibold text-slate-900">
          Overview
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">
                    {metric.label}
                  </p>
                  <p className="mt-2 font-serif text-3xl font-bold text-slate-900">
                    {metric.value}
                  </p>
                </div>
                {metric.icon && (
                  <span className="text-4xl">{metric.icon}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Onboarding Metrics */}
      {onboardingMetrics && (
        <section className="mb-8">
          <h2 className="mb-4 font-serif text-lg font-semibold text-slate-900">
            Onboarding Metrics
          </h2>
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="text-sm font-medium text-slate-600">Started</p>
                <p className="mt-1 font-serif text-2xl font-bold text-slate-900">
                  {onboardingMetrics.total_started}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-600">Completed</p>
                <p className="mt-1 font-serif text-2xl font-bold text-slate-900">
                  {onboardingMetrics.total_completed}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-600">
                  Completion Rate
                </p>
                <p className="mt-1 font-serif text-2xl font-bold text-slate-900">
                  {formatPercentage(onboardingMetrics.completion_rate)}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-600">
                  Avg Time to First Value
                </p>
                <p className="mt-1 font-serif text-2xl font-bold text-slate-900">
                  {formatDuration(
                    onboardingMetrics.average_time_to_first_value_ms
                  )}
                </p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Recent Activity */}
      <section>
        <h2 className="mb-4 font-serif text-lg font-semibold text-slate-900">
          Recent Activity
        </h2>
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          {activity.length === 0 ? (
            <p className="p-6 text-center text-slate-500">No recent activity</p>
          ) : (
            <ul className="divide-y divide-slate-200">
              {activity.map((item) => (
                <li key={item.id} className="flex items-center gap-4 p-4">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-lg">
                    {item.type === "brand" && "🏢"}
                    {item.type === "project" && "📁"}
                    {item.type === "thread" && "💬"}
                    {item.type === "run" && "⚡"}
                  </span>
                  <div className="flex-1">
                    <p className="font-medium text-slate-900">{item.name}</p>
                    <p className="text-sm text-slate-600">
                      {item.action} •{" "}
                      <span className="capitalize">{item.type}</span>
                    </p>
                  </div>
                  <span className="text-sm text-slate-500">
                    {formatRelativeTime(item.timestamp)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
