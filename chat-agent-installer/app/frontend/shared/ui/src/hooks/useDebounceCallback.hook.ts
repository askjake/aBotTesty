import { useCallback, useRef } from 'react';

const useDebouncedCallback = (func: (value: any) => void, wait = 200) => {
  const timeout = useRef<any>(null);

  return useCallback(
    (...args: any[]) => {
      const later = () => {
        clearTimeout(timeout.current);
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-expect-error
        func(...args);
      };

      clearTimeout(timeout.current);
      timeout.current = setTimeout(later, wait);
    },
    [func, wait],
  );
};

export default useDebouncedCallback;
