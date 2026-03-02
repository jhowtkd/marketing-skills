export interface FunnelStage {
  id: string;
  name: string;
  order: number;
}

interface StageMetrics {
  id: string;
  name: string;
  order: number;
  entries: number;
  uniqueUsers: string[];
  avgTimeSpent: number;
  conversionRate: number;
  totalTimeSpent: number;
  userTimestamps: Map<string, number>;
}

interface FunnelData {
  id: string;
  stages: FunnelStage[];
  stageMetrics: Map<string, StageMetrics>;
  navigationAttempts: number;
  navigationErrors: number;
}

interface FunnelMetrics {
  id: string;
  stages: Array<{
    id: string;
    name: string;
    order: number;
    entries: number;
    uniqueUsers: string[];
    avgTimeSpent: number;
    conversionRate: number;
  }>;
  overallConversionRate: number;
  timeToFirstAction: number | null;
  navigationErrorRate: number;
  workflowCompletionRate: number;
}

interface DropOffPoint {
  stageId: string;
  stageName: string;
  dropOffRate: number;
  dropOffCount: number;
}

const funnels: Map<string, FunnelData> = new Map();

export function createFunnel(id: string, stages: FunnelStage[]): FunnelData {
  // Sort stages by order
  const sortedStages = [...stages].sort((a, b) => a.order - b.order);
  
  const stageMetrics = new Map<string, StageMetrics>();
  
  for (const stage of sortedStages) {
    stageMetrics.set(stage.id, {
      id: stage.id,
      name: stage.name,
      order: stage.order,
      entries: 0,
      uniqueUsers: [],
      avgTimeSpent: 0,
      conversionRate: 0,
      totalTimeSpent: 0,
      userTimestamps: new Map(),
    });
  }
  
  const funnel: FunnelData = {
    id,
    stages: sortedStages,
    stageMetrics,
    navigationAttempts: 0,
    navigationErrors: 0,
  };
  
  funnels.set(id, funnel);
  return funnel;
}

export function trackFunnelStep(funnelId: string, stageId: string, userId: string): void {
  const funnel = funnels.get(funnelId);
  if (!funnel) {
    throw new Error(`Funnel ${funnelId} not found`);
  }
  
  const metrics = funnel.stageMetrics.get(stageId);
  if (!metrics) {
    throw new Error(`Stage ${stageId} not found in funnel ${funnelId}`);
  }
  
  const timestamp = Date.now();
  const stageIndex = funnel.stages.findIndex(s => s.id === stageId);
  
  // Track unique users
  if (!metrics.uniqueUsers.includes(userId)) {
    metrics.uniqueUsers.push(userId);
  }
  
  // Calculate time spent if user was in previous stage
  if (stageIndex > 0) {
    const previousStage = funnel.stages[stageIndex - 1];
    const previousMetrics = funnel.stageMetrics.get(previousStage.id);
    if (previousMetrics && previousMetrics.userTimestamps.has(userId)) {
      const entryTime = previousMetrics.userTimestamps.get(userId)!;
      const timeSpent = timestamp - entryTime;
      previousMetrics.totalTimeSpent += timeSpent;
      previousMetrics.avgTimeSpent = previousMetrics.totalTimeSpent / previousMetrics.entries;
    }
  }
  
  // Track navigation attempts and errors
  if (stageIndex === 0) {
    // First stage entry = new navigation attempt
    funnel.navigationAttempts++;
  } else if (stageIndex === 1) {
    // Second stage entry = successful navigation
    // Navigation error is when users enter stage 0 but not stage 1
    // We'll calculate errors in getFunnelMetrics
  }
  
  // Record entry timestamp for this stage
  if (!metrics.userTimestamps.has(userId)) {
    metrics.entries++;
  }
  metrics.userTimestamps.set(userId, timestamp);
  
  // Update conversion rates
  updateConversionRates(funnel);
}

function updateConversionRates(funnel: FunnelData): void {
  // Stage 1 always has 100% conversion (entry point)
  // Subsequent stages convert relative to their previous stage
  
  for (let i = 0; i < funnel.stages.length; i++) {
    const stage = funnel.stages[i];
    const metrics = funnel.stageMetrics.get(stage.id);
    if (!metrics) continue;
    
    if (i === 0) {
      // Entry point: 100%
      metrics.conversionRate = 1;
    } else {
      // Convert relative to previous stage
      const prevStage = funnel.stages[i - 1];
      const prevMetrics = funnel.stageMetrics.get(prevStage.id);
      const prevEntries = prevMetrics?.entries || 1;
      metrics.conversionRate = metrics.entries / prevEntries;
    }
  }
}

export function getFunnelMetrics(funnelId: string): FunnelMetrics | null {
  const funnel = funnels.get(funnelId);
  if (!funnel) {
    return null;
  }
  
  const stages: FunnelMetrics['stages'] = [];
  const firstStage = funnel.stages[0];
  const firstMetrics = funnel.stageMetrics.get(firstStage.id);
  const totalEntries = firstMetrics?.entries || 1;
  
  for (const stage of funnel.stages) {
    const metrics = funnel.stageMetrics.get(stage.id);
    if (metrics) {
      stages.push({
        id: metrics.id,
        name: metrics.name,
        order: metrics.order,
        entries: metrics.entries,
        uniqueUsers: [...metrics.uniqueUsers],
        avgTimeSpent: Math.round(metrics.avgTimeSpent),
        conversionRate: Math.round(metrics.conversionRate * 100) / 100,
      });
    }
  }
  
  // Calculate overall conversion rate (last stage entries / first stage entries)
  const lastStage = funnel.stages[funnel.stages.length - 1];
  const lastMetrics = funnel.stageMetrics.get(lastStage.id);
  const overallConversionRate = lastMetrics 
    ? (lastMetrics.entries / totalEntries) 
    : 0;
  
  // Calculate time to first action (stage 2 timestamp - stage 1 timestamp for users who completed both)
  let timeToFirstAction: number | null = null;
  if (funnel.stages.length >= 2) {
    const firstStageMetrics = funnel.stageMetrics.get(funnel.stages[0].id);
    const secondStageMetrics = funnel.stageMetrics.get(funnel.stages[1].id);
    
    if (firstStageMetrics && secondStageMetrics) {
      let totalTime = 0;
      let count = 0;
      
      for (const userId of secondStageMetrics.uniqueUsers) {
        const firstTime = firstStageMetrics.userTimestamps.get(userId);
        const secondTime = secondStageMetrics.userTimestamps.get(userId);
        if (firstTime && secondTime) {
          totalTime += secondTime - firstTime;
          count++;
        }
      }
      
      if (count > 0) {
        timeToFirstAction = Math.round(totalTime / count);
      }
    }
  }
  
  // Calculate navigation error rate (users who entered first but not second stage)
  let navigationErrorRate = 0;
  if (funnel.stages.length >= 2) {
    const firstStageMetrics = funnel.stageMetrics.get(funnel.stages[0].id);
    const secondStageMetrics = funnel.stageMetrics.get(funnel.stages[1].id);
    
    if (firstStageMetrics && secondStageMetrics) {
      // Navigation errors = users in stage 1 who never made it to stage 2
      // However, we need to be careful - not all stage 1 users attempted navigation to stage 2
      // For this metric, we'll calculate: (stage1_entries - stage2_entries) / stage1_entries
      // This gives us the percentage of users who dropped off between stage 1 and 2
      const errors = firstStageMetrics.entries - secondStageMetrics.entries;
      navigationErrorRate = errors / (firstStageMetrics.entries || 1);
    }
  }
  
  // Calculate workflow completion rate (last stage entries / first stage entries)
  const workflowCompletionRate = overallConversionRate;
  
  return {
    id: funnel.id,
    stages,
    overallConversionRate: Math.round(overallConversionRate * 100) / 100,
    timeToFirstAction,
    navigationErrorRate: Math.round(navigationErrorRate * 100) / 100,
    workflowCompletionRate: Math.round(workflowCompletionRate * 100) / 100,
  };
}

export function getFunnelDropOffPoints(funnelId: string): DropOffPoint[] {
  const funnel = funnels.get(funnelId);
  if (!funnel) {
    return [];
  }
  
  const dropOffs: DropOffPoint[] = [];
  
  for (let i = 0; i < funnel.stages.length - 1; i++) {
    const currentStage = funnel.stages[i];
    const nextStage = funnel.stages[i + 1];
    
    const currentMetrics = funnel.stageMetrics.get(currentStage.id);
    const nextMetrics = funnel.stageMetrics.get(nextStage.id);
    
    if (currentMetrics && nextMetrics) {
      const dropOffCount = currentMetrics.entries - nextMetrics.entries;
      const dropOffRate = dropOffCount / (currentMetrics.entries || 1);
      
      if (dropOffCount > 0) {
        dropOffs.push({
          stageId: currentStage.id,
          stageName: currentStage.name,
          dropOffRate: Math.round(dropOffRate * 100) / 100,
          dropOffCount,
        });
      }
    }
  }
  
  // Sort by drop-off rate descending
  return dropOffs.sort((a, b) => b.dropOffRate - a.dropOffRate);
}

export function resetFunnel(): void {
  funnels.clear();
}
