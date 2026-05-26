import '@testing-library/jest-dom';
import 'jest-styled-components';
jest.setTimeout(30000);
beforeAll(() => {
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-expect-error
  global.IS_REACT_ACT_ENVIRONMENT = true;
});
class MockReadableStream {
  locked = false;

  getReader() {
    return {
      read: () => Promise.resolve({ done: true, value: undefined }),
      releaseLock: () => {},
    };
  }
}

global.matchMedia =
  global.matchMedia ||
  function () {
    return {
      matches: false,
      addListener: jest.fn(),
      removeListener: jest.fn(),
    };
  };

(global as any).ReadableStream = MockReadableStream;

global.DataTransfer = jest.fn().mockImplementation(() => ({
  items: {
    add: jest.fn(),
  },
  files: [],
}));

// In jest.setup.ts, replace the existing MockFileList with this:

// In jest.setup.ts, replace the existing MockFileList with this:

// In jest.setup.ts, replace the MockFileList section with this:

// Store the original FileList if it exists
const OriginalFileList = global.FileList;

// Create a proper mock that will pass instanceof checks
function MockFileList(files: File[] = []) {
  // Create an object that inherits from FileList.prototype
  const instance = Object.create(OriginalFileList?.prototype || {});

  // Set the constructor
  instance.constructor = MockFileList;

  // Add files as indexed properties
  files.forEach((file, index) => {
    instance[index] = file;
  });

  // Set length
  Object.defineProperty(instance, 'length', {
    value: files.length,
    writable: false,
    enumerable: false,
    configurable: false,
  });

  // Add required methods
  instance.item = function (index: number): File | null {
    return this[index] || null;
  };

  instance[Symbol.iterator] = function* () {
    for (let i = 0; i < this.length; i++) {
      yield this[i];
    }
  };

  instance.forEach = function (callback: (file: File, index: number) => void) {
    for (let i = 0; i < this.length; i++) {
      callback(this[i], i);
    }
  };

  return instance;
}

// Set up the prototype chain
MockFileList.prototype = OriginalFileList?.prototype || {};
MockFileList.prototype.constructor = MockFileList;

// Replace global FileList
global.FileList = MockFileList as any;

jest.mock('nanoid', () => {
  let counter = 0;
  return {
    nanoid: () => {
      counter += 1;
      return `test-id-${counter}`;
    },
    customAlphabet: () => () => {
      counter += 1;
      return `test-id-${counter}`;
    },
  };
});

global.ResizeObserver = class ResizeObserver {
  observe() {
    // do nothing
  }
  unobserve() {
    // do nothing
  }
  disconnect() {
    // do nothing
  }
};
