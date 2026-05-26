export const omitKeys = ({
  obj,
  keysToRemove = [],
}: {
  obj: { [key: string]: any };
  keysToRemove: string[];
}) =>
  Object.fromEntries(
    Object.entries(obj).filter(
      ([key]) => !keysToRemove.includes(key.toLowerCase()),
    ),
  );

export const pickKeys = ({
  obj,
  keysToPick = [],
}: {
  obj: { [key: string]: any };
  keysToPick: string[];
}) =>
  Object.fromEntries(
    Object.entries(obj).filter(([key]) =>
      keysToPick.includes(key.toLowerCase()),
    ),
  );

export const delay = (ms = 1000) =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const isIndexedDBSupported = (): boolean => {
  try {
    return typeof window !== 'undefined' && 'indexedDB' in window;
  } catch {
    return false;
  }
};
