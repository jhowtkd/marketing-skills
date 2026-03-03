import { useRef, useEffect, type ReactNode } from "react";

interface InfiniteScrollListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
  keyExtractor: (item: T) => string;
  onLoadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
  loadingComponent?: ReactNode;
  emptyComponent?: ReactNode;
  className?: string;
  threshold?: number;
}

export default function InfiniteScrollList<T>({
  items,
  renderItem,
  keyExtractor,
  onLoadMore,
  hasMore,
  isLoading,
  loadingComponent,
  emptyComponent,
  className = "",
  threshold = 100,
}: InfiniteScrollListProps<T>): JSX.Element {
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoading) {
          onLoadMore();
        }
      },
      { rootMargin: `${threshold}px` }
    );

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    return () => {
      observerRef.current?.disconnect();
    };
  }, [hasMore, isLoading, onLoadMore, threshold]);

  if (items.length === 0 && !isLoading) {
    return <>{emptyComponent || <p className="text-sm text-slate-500">No items</p>}</>;
  }

  return (
    <div className={className}>
      {items.map((item, index) => (
        <div key={keyExtractor(item)}>{renderItem(item, index)}</div>
      ))}

      {/* Load more trigger */}
      {hasMore && (
        <div ref={loadMoreRef} className="py-2">
          {isLoading
            ? loadingComponent || (
                <div className="flex items-center justify-center py-4">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-primary"></div>
                </div>
              )
            : null}
        </div>
      )}
    </div>
  );
}

// Simple Load More Button variant
interface LoadMoreButtonProps {
  onLoadMore: () => void;
  hasMore: boolean;
  isLoading: boolean;
  className?: string;
}

export function LoadMoreButton({
  onLoadMore,
  hasMore,
  isLoading,
  className = "",
}: LoadMoreButtonProps): JSX.Element | null {
  if (!hasMore) return null;

  return (
    <button
      onClick={onLoadMore}
      disabled={isLoading}
      className={[
        "w-full rounded-lg border border-slate-200 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-50",
        className,
      ].join(" ")}
    >
      {isLoading ? (
        <span className="flex items-center justify-center gap-2">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-400 border-t-transparent"></span>
          Loading...
        </span>
      ) : (
        "Load more"
      )}
    </button>
  );
}
