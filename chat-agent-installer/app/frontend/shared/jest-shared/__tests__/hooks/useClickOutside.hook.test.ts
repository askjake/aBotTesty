import { renderHook } from '@testing-library/react';
import { fireEvent } from '@testing-library/dom';
import { RefObject } from 'react';
import { InputRef } from 'antd';
import useClickOutside from '@shared/ui/hooks/useClickOutside.hook';

// Mock InputRef for testing
const createMockInputRef = (element: HTMLElement | null = null): InputRef => ({
  focus: jest.fn(),
  blur: jest.fn(),
  select: jest.fn(),
  input: element as HTMLInputElement,
  nativeElement: element,
  setSelectionRange: function (): void {
    throw new Error('Function not implemented.');
  },
});

describe('useClickOutside', () => {
  let mockCallback: jest.MockedFunction<(event: MouseEvent) => void>;
  let container: HTMLDivElement;

  beforeEach(() => {
    mockCallback = jest.fn();
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
    jest.clearAllMocks();
  });

  describe('HTMLDivElement ref', () => {
    it('should call callback when clicking outside the referenced div element', () => {
      const divElement = document.createElement('div');
      container.appendChild(divElement);

      const ref: RefObject<HTMLDivElement> = { current: divElement };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(container);

      expect(mockCallback).toHaveBeenCalledTimes(1);
      expect(mockCallback).toHaveBeenCalledWith(expect.any(MouseEvent));
    });

    it('should not call callback when clicking inside the referenced div element', () => {
      const divElement = document.createElement('div');
      container.appendChild(divElement);

      const ref: RefObject<HTMLDivElement> = { current: divElement };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(divElement);

      expect(mockCallback).not.toHaveBeenCalled();
    });
  });

  describe('HTMLInputElement ref', () => {
    it('should call callback when clicking outside the referenced input element', () => {
      const inputElement = document.createElement('input');
      container.appendChild(inputElement);

      const ref: RefObject<HTMLInputElement> = { current: inputElement };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(container);

      expect(mockCallback).toHaveBeenCalledTimes(1);
    });

    it('should not call callback when clicking inside the referenced input element', () => {
      const inputElement = document.createElement('input');
      container.appendChild(inputElement);

      const ref: RefObject<HTMLInputElement> = { current: inputElement };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(inputElement);

      expect(mockCallback).not.toHaveBeenCalled();
    });
  });

  describe('Antd InputRef', () => {
    it('should call callback when clicking outside InputRef with nativeElement', () => {
      const inputElement = document.createElement('input');
      container.appendChild(inputElement);

      const inputRef = createMockInputRef(inputElement);
      const ref: RefObject<InputRef> = { current: inputRef };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(container);

      expect(mockCallback).toHaveBeenCalledTimes(1);
    });

    it('should not call callback when clicking inside InputRef with nativeElement', () => {
      const inputElement = document.createElement('input');
      container.appendChild(inputElement);

      const inputRef = createMockInputRef(inputElement);
      const ref: RefObject<InputRef> = { current: inputRef };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(inputElement);

      expect(mockCallback).not.toHaveBeenCalled();
    });

    it('should call callback when InputRef has no nativeElement (fallback behavior)', () => {
      // This test reflects the actual behavior of your hook
      // When nativeElement is null, it falls back to ref.current (InputRef object)
      // Since InputRef doesn't have contains method, the callback gets triggered
      const inputRef = createMockInputRef(null);
      const ref: RefObject<InputRef> = { current: inputRef };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(container);

      // This is the actual behavior - callback gets called because
      // InputRef object doesn't have contains method
      expect(mockCallback).toHaveBeenCalledTimes(1);
    });
  });

  describe('Edge cases', () => {
    it('should not call callback when ref.current is null', () => {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      const ref: RefObject<HTMLDivElement> = { current: null };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(container);

      expect(mockCallback).not.toHaveBeenCalled();
    });

    it('should not call callback when ref is null/undefined', () => {
      const ref = { current: undefined } as any;

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(container);

      expect(mockCallback).not.toHaveBeenCalled();
    });

    it('should handle clicks on child elements correctly', () => {
      const divElement = document.createElement('div');
      const childElement = document.createElement('span');
      divElement.appendChild(childElement);
      container.appendChild(divElement);

      const ref: RefObject<HTMLDivElement> = { current: divElement };

      renderHook(() => useClickOutside(ref, mockCallback));

      fireEvent.mouseDown(childElement);

      expect(mockCallback).not.toHaveBeenCalled();
    });

    it('should call callback when element does not have contains method', () => {
      // This reflects actual behavior - when contains is not available, callback is triggered
      const mockElement = {} as any;
      const ref: RefObject<any> = { current: mockElement };

      renderHook(() => useClickOutside(ref, mockCallback));
      fireEvent.mouseDown(container);

      expect(mockCallback).toHaveBeenCalledTimes(1);
    });

    it('should handle event target that is not a Node', () => {
      const divElement = document.createElement('div');
      container.appendChild(divElement);

      const ref: RefObject<HTMLDivElement> = { current: divElement };

      renderHook(() => useClickOutside(ref, mockCallback));

      const customEvent = new MouseEvent('mousedown', { bubbles: true });
      Object.defineProperty(customEvent, 'target', {
        value: null,
        writable: false,
      });

      expect(() => {
        document.dispatchEvent(customEvent);
      }).not.toThrow();
    });
  });

  describe('Event listener management', () => {
    it('should add event listener on mount', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      const divElement = document.createElement('div');
      const ref: RefObject<HTMLDivElement> = { current: divElement };

      renderHook(() => useClickOutside(ref, mockCallback));

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        'mousedown',
        expect.any(Function),
      );

      addEventListenerSpy.mockRestore();
    });

    it('should remove event listener on unmount', () => {
      const removeEventListenerSpy = jest.spyOn(
        document,
        'removeEventListener',
      );
      const divElement = document.createElement('div');
      const ref: RefObject<HTMLDivElement> = { current: divElement };

      const { unmount } = renderHook(() => useClickOutside(ref, mockCallback));

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'mousedown',
        expect.any(Function),
      );

      removeEventListenerSpy.mockRestore();
    });

    it('should update event listener when dependencies change', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(
        document,
        'removeEventListener',
      );

      const divElement1 = document.createElement('div');
      const divElement2 = document.createElement('div');
      container.appendChild(divElement1);
      container.appendChild(divElement2);

      const { rerender } = renderHook(
        ({ ref, callback }) => useClickOutside(ref, callback),
        {
          initialProps: {
            ref: { current: divElement1 },
            callback: mockCallback,
          },
        },
      );

      const newCallback = jest.fn();
      rerender({
        ref: { current: divElement2 },
        callback: newCallback,
      });

      expect(removeEventListenerSpy).toHaveBeenCalled();
      expect(addEventListenerSpy).toHaveBeenCalledTimes(2);

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });

  describe('Multiple elements scenario', () => {
    it('should work correctly with multiple instances', () => {
      const div1 = document.createElement('div');
      const div2 = document.createElement('div');
      container.appendChild(div1);
      container.appendChild(div2);

      const ref1: RefObject<HTMLDivElement> = { current: div1 };
      const ref2: RefObject<HTMLDivElement> = { current: div2 };
      const callback1 = jest.fn();
      const callback2 = jest.fn();

      renderHook(() => useClickOutside(ref1, callback1));
      renderHook(() => useClickOutside(ref2, callback2));

      // Click outside both elements
      fireEvent.mouseDown(container);

      expect(callback1).toHaveBeenCalledTimes(1);
      expect(callback2).toHaveBeenCalledTimes(1);

      jest.clearAllMocks();

      // Click on first element
      fireEvent.mouseDown(div1);

      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).toHaveBeenCalledTimes(1);
    });
  });

  describe('Real-world usage scenarios', () => {
    it('should work with nested elements', () => {
      const parentDiv = document.createElement('div');
      const childDiv = document.createElement('div');
      const grandchildSpan = document.createElement('span');

      childDiv.appendChild(grandchildSpan);
      parentDiv.appendChild(childDiv);
      container.appendChild(parentDiv);

      const ref: RefObject<HTMLDivElement> = { current: parentDiv };

      renderHook(() => useClickOutside(ref, mockCallback));

      // Click on deeply nested child - should not trigger callback
      fireEvent.mouseDown(grandchildSpan);
      expect(mockCallback).not.toHaveBeenCalled();

      // Click outside - should trigger callback
      fireEvent.mouseDown(container);
      expect(mockCallback).toHaveBeenCalledTimes(1);
    });

    it('should handle rapid successive clicks correctly', () => {
      const divElement = document.createElement('div');
      container.appendChild(divElement);

      const ref: RefObject<HTMLDivElement> = { current: divElement };

      renderHook(() => useClickOutside(ref, mockCallback));

      // Multiple rapid clicks outside
      fireEvent.mouseDown(container);
      fireEvent.mouseDown(container);
      fireEvent.mouseDown(container);

      expect(mockCallback).toHaveBeenCalledTimes(3);

      jest.clearAllMocks();

      // Multiple rapid clicks inside
      fireEvent.mouseDown(divElement);
      fireEvent.mouseDown(divElement);
      fireEvent.mouseDown(divElement);

      expect(mockCallback).not.toHaveBeenCalled();
    });
  });
});
