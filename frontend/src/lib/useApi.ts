import { useEffect, useState } from "react";

interface ApiState<T> {
  data: T | null;
  error: Error | null;
}

/**
 * Load data whenever deps change; late responses for old deps are ignored.
 * The previous data stays visible while reloading, so polling doesn't flicker.
 */
export function useApi<T>(load: () => Promise<T>, deps: unknown[]): ApiState<T> {
  const key = JSON.stringify(deps);
  const [state, setState] = useState<ApiState<T>>({ data: null, error: null });

  useEffect(() => {
    let isCurrent = true;
    load().then(
      (data) => {
        if (isCurrent) setState({ data, error: null });
      },
      (error: Error) => {
        if (isCurrent) setState({ data: null, error });
      },
    );
    return () => {
      isCurrent = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deps are serialized into key
  }, [key]);

  return state;
}
