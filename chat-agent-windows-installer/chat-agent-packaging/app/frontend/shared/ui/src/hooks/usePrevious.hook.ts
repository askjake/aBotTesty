import { useRef } from 'react';

export const usePrevious = (value: any) => {
  const currentRef = useRef(value);
  const previousRef = useRef(null);

  // const forceUpdate = useCallback(
  //   (newValue: any) => (previousRef.current = newValue),
  //   [],
  // );

  if (currentRef.current !== value) {
    previousRef.current = currentRef.current;
    currentRef.current = value;
  }
  //
  // if (withForceUpdate) {
  //   return [previousRef.current, forceUpdate];
  // }

  return previousRef.current;
};

export default usePrevious;
