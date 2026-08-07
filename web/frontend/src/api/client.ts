/** 类型化 API client 与请求 hook。前端只消费后端 JSON，不做任何统计推导。 */

import { useCallback, useEffect, useState } from "react";

const API_PREFIX = "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    let detail = `请求失败（HTTP ${response.status}）`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // 响应体不是 JSON 时保留默认提示。
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * 拉取单个资源。path 变化时自动重新请求，组件卸载时取消。
 * path 为 null 表示暂不请求。
 */
export function useResource<T>(path: string | null): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(path !== null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    if (path === null) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    request<T>(path, controller.signal)
      .then((payload) => {
        setData(payload);
        setLoading(false);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setData(null);
        setError(cause instanceof Error ? cause.message : "未知错误");
        setLoading(false);
      });
    return () => controller.abort();
  }, [path, attempt]);

  return { data, loading, error, reload };
}

/** 手动触发的请求，用于 checksum 校验这类明确的慢操作。 */
export function useLazyResource<T>(path: string): AsyncState<T> & { run: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(() => {
    setLoading(true);
    setError(null);
    request<T>(path)
      .then((payload) => {
        setData(payload);
        setLoading(false);
      })
      .catch((cause: unknown) => {
        setData(null);
        setError(cause instanceof Error ? cause.message : "未知错误");
        setLoading(false);
      });
  }, [path]);

  return { data, loading, error, reload: run, run };
}
