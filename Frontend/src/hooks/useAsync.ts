import { useEffect, useState } from 'react';

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error>();

  const run = async () => {
    setLoading(true);
    setError(undefined);
    try {
      setData(await fn());
    } catch (exception) {
      setError(exception as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void run();
    // The caller controls refreshes with its explicit dependency list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, reload: run };
}
