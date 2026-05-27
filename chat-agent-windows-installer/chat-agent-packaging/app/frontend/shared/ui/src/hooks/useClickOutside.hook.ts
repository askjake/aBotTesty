import { RefObject, useEffect } from 'react';
import { InputRef } from 'antd';

type CallbackFunction = (event: MouseEvent) => void;

const useClickOutside = (
  ref: RefObject<HTMLInputElement | HTMLDivElement | InputRef | null>,
  callback: CallbackFunction,
): void => {
  useEffect(() => {
    const handleClick = (event: MouseEvent): void => {
      if (!ref?.current) return;

      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      const currentRef = ref.current.nativeElement ?? ref.current;
      if (currentRef && !currentRef?.contains?.(event.target as Node)) {
        callback(event);
      }
    };

    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [ref, callback]);
};

export default useClickOutside;
