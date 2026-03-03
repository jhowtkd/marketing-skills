import { useState, useEffect, useCallback, useRef } from "react";

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  hasMore: boolean;
  nextCursor?: string;
}

interface UseInfiniteScrollOptions<T> {
  fetchPage: (cursor?: string) => Promise<PaginatedResponse<T>>;
  pageSize?: number;
  enabled?: boolean;
}

interface UseInfiniteScrollResult<T> {
  items: T[];
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  loadMore: () => void;
  refresh: () => void;
}

export function useInfiniteScroll<T>({
  fetchPage,
  enabled = true,
}: UseInfiniteScrollOptions<T>): UseInfiniteScrollResult<T> {
  const [items, setItems] = useState<T[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const isFetchingRef = useRef(false);

  const fetchData = useCallback(
    async (isInitial: boolean) => {
      if (!enabled || isFetchingRef.current) return;

      isFetchingRef.current = true;

      if (isInitial) {
        setIsLoading(true);
      } else {
        setIsLoadingMore(true);
      }

      try {
        const response = await fetchPage(isInitial ? undefined : cursor);

        if (isInitial) {
          setItems(response.items);
        } else {
          setItems((prev) => [...prev, ...response.items]);
        }

        setHasMore(response.hasMore);
        setCursor(response.nextCursor);
        setError(null);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load items";
        setError(message);
      } finally {
        setIsLoading(false);
        setIsLoadingMore(false);
        isFetchingRef.current = false;
      }
    },
    [fetchPage, cursor, enabled]
  );

  // Initial load
  useEffect(() => {
    if (enabled) {
      fetchData(true);
    }
  }, [enabled, fetchData]);

  const loadMore = useCallback(() => {
    if (!isLoading && !isLoadingMore && hasMore) {
      fetchData(false);
    }
  }, [isLoading, isLoadingMore, hasMore, fetchData]);

  const refresh = useCallback(() => {
    setCursor(undefined);
    setHasMore(true);
    fetchData(true);
  }, [fetchData]);

  return {
    items,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    loadMore,
    refresh,
  };
}

// Hook for intersection observer (trigger load on scroll)
export function useIntersectionObserver(
  callback: () => void,
  options?: IntersectionObserverInit
) {
  const targetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const target = targetRef.current;
    if (!target) return;

    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        callback();
      }
    }, options);

    observer.observe(target);

    return () => {
      observer.disconnect();
    };
  }, [callback, options]);

  return targetRef;
}

// Simple paginated list hook (non-infinite)
interface UsePaginatedListOptions<T> {
  fetchItems: (page: number, pageSize: number) => Promise<T[]>;
  pageSize?: number;
  enabled?: boolean;
}

interface UsePaginatedListResult<T> {
  items: T[];
  page: number;
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  nextPage: () => void;
  prevPage: () => void;
  goToPage: (page: number) => void;
  refresh: () => void;
}

export function usePaginatedList<T>({
  fetchItems,
  pageSize = 20,
  enabled = true,
}: UsePaginatedListOptions<T>): UsePaginatedListResult<T> {
  const [items, setItems] = useState<T[]>([]);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const fetchData = useCallback(
    async (targetPage: number) => {
      if (!enabled) return;

      setIsLoading(true);
      try {
        const newItems = await fetchItems(targetPage, pageSize);
        setItems(newItems);
        setHasMore(newItems.length === pageSize);
        setError(null);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load items";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [fetchItems, pageSize, enabled]
  );

  useEffect(() => {
    fetchData(page);
  }, [page, fetchData]);

  const nextPage = useCallback(() => {
    if (hasMore && !isLoading) {
      setPage((p) => p + 1);
    }
  }, [hasMore, isLoading]);

  const prevPage = useCallback(() => {
    if (page > 1 && !isLoading) {
      setPage((p) => p - 1);
    }
  }, [page, isLoading]);

  const goToPage = useCallback(
    (targetPage: number) => {
      if (targetPage >= 1 && !isLoading) {
        setPage(targetPage);
      }
    },
    [isLoading]
  );

  const refresh = useCallback(() => {
    fetchData(page);
  }, [fetchData, page]);

  return {
    items,
    page,
    isLoading,
    error,
    hasMore,
    nextPage,
    prevPage,
    goToPage,
    refresh,
  };
}
