import { renderHook } from '@testing-library/react';
import usePrevious from '@shared/ui/hooks/usePrevious.hook';

describe('usePrevious', () => {
  it('should return null on initial render', () => {
    const { result } = renderHook(() => usePrevious('initial'));

    expect(result.current).toBeNull();
  });

  it('should return previous value after rerender with new value', () => {
    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: 'first' },
    });

    // Initial render should return null
    expect(result.current).toBeNull();

    // Rerender with new value
    rerender({ value: 'second' });
    expect(result.current).toBe('first');

    // Rerender with another new value
    rerender({ value: 'third' });
    expect(result.current).toBe('second');
  });

  it('should return same previous value when rerendered with same value', () => {
    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: 'same' },
    });

    expect(result.current).toBeNull();

    rerender({ value: 'different' });
    expect(result.current).toBe('same');

    // Rerender with same value - should keep previous value
    rerender({ value: 'different' });
    expect(result.current).toBe('same');
  });

  it('should work with different data types', () => {
    // Test with numbers
    const { result: numberResult, rerender: numberRerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: 1 } },
    );

    numberRerender({ value: 2 });
    expect(numberResult.current).toBe(1);

    // Test with booleans
    const { result: boolResult, rerender: boolRerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: true } },
    );

    boolRerender({ value: false });
    expect(boolResult.current).toBe(true);

    // Test with objects
    const obj1 = { id: 1, name: 'first' };
    const obj2 = { id: 2, name: 'second' };

    const { result: objResult, rerender: objRerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: obj1 } },
    );

    objRerender({ value: obj2 });
    expect(objResult.current).toBe(obj1);

    // Test with arrays
    const arr1 = [1, 2, 3];
    const arr2 = [4, 5, 6];

    const { result: arrResult, rerender: arrRerender } = renderHook(
      ({ value }) => usePrevious(value),
      { initialProps: { value: arr1 } },
    );

    arrRerender({ value: arr2 });
    expect(arrResult.current).toBe(arr1);
  });

  it('should handle null and undefined values', () => {
    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: null },
    });

    expect(result.current).toBeNull();

    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    rerender({ value: undefined });
    expect(result.current).toBeNull();

    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    rerender({ value: 'defined' });
    expect(result.current).toBeUndefined();

    rerender({ value: null });
    expect(result.current).toBe('defined');
  });

  it('should handle zero and falsy values correctly', () => {
    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: 0 },
    });

    expect(result.current).toBeNull();
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    rerender({ value: false });
    expect(result.current).toBe(0);
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    rerender({ value: '' });
    expect(result.current).toBe(false);

    rerender({ value: 1 });
    expect(result.current).toBe('');
  });

  it('should maintain reference equality for objects', () => {
    const obj1 = { id: 1 };
    const obj2 = { id: 1 }; // Same content, different reference

    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: obj1 },
    });

    rerender({ value: obj2 });
    expect(result.current).toBe(obj1); // Should be the exact same reference
    expect(result.current).not.toBe(obj2); // Different reference even with same content
  });

  it('should work with complex nested objects', () => {
    const complex1 = {
      user: { id: 1, profile: { name: 'John', settings: { theme: 'dark' } } },
      data: [1, 2, 3],
    };

    const complex2 = {
      user: { id: 2, profile: { name: 'Jane', settings: { theme: 'light' } } },
      data: [4, 5, 6],
    };

    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: complex1 },
    });

    rerender({ value: complex2 });
    expect(result.current).toBe(complex1);
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    expect(result.current?.user.profile.name).toBe('John');
  });

  it('should handle rapid value changes', () => {
    const { result, rerender } = renderHook(({ value }) => usePrevious(value), {
      initialProps: { value: 'a' },
    });

    const values = ['b', 'c', 'd', 'e'];
    const expectedPrevious = ['a', 'b', 'c', 'd'];

    values.forEach((value, index) => {
      rerender({ value });
      expect(result.current).toBe(expectedPrevious[index]);
    });
  });
});
