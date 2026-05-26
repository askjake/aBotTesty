// Adjust the import path as needed

import { omitKeys, pickKeys } from '@shared/ui/utils/common.utils';

describe('Object Utils', () => {
  describe('omitKeys', () => {
    it('should return an empty object when given an empty object', () => {
      const result = omitKeys({ obj: {}, keysToRemove: ['key1', 'key2'] });
      expect(result).toEqual({});
    });

    it('should return the same object when keysToRemove is empty', () => {
      const testObj = { key1: 'value1', key2: 'value2' };
      const result = omitKeys({ obj: testObj, keysToRemove: [] });
      expect(result).toEqual(testObj);
    });

    it('should remove specified keys from the object', () => {
      const testObj = {
        key1: 'value1',
        key2: 'value2',
        key3: 'value3',
        key4: 'value4',
      };
      const result = omitKeys({ obj: testObj, keysToRemove: ['key1', 'key3'] });
      expect(result).toEqual({
        key2: 'value2',
        key4: 'value4',
      });
    });

    it('should handle case-insensitive key matching', () => {
      const testObj = {
        Key1: 'value1',
        KEY2: 'value2',
        key3: 'value3',
        kEy4: 'value4',
      };
      const result = omitKeys({ obj: testObj, keysToRemove: ['key1', 'key3'] });
      expect(result).toEqual({
        KEY2: 'value2',
        kEy4: 'value4',
      });
    });

    it('should handle keys that do not exist in the object', () => {
      const testObj = {
        key1: 'value1',
        key2: 'value2',
      };
      const result = omitKeys({ obj: testObj, keysToRemove: ['key3', 'key4'] });
      expect(result).toEqual(testObj);
    });

    it('should handle objects with non-string values', () => {
      const testObj = {
        key1: 123,
        key2: true,
        key3: { nestedKey: 'value' },
        key4: [1, 2, 3],
      };
      const result = omitKeys({ obj: testObj, keysToRemove: ['key1', 'key3'] });
      expect(result).toEqual({
        key2: true,
        key4: [1, 2, 3],
      });
    });

    it('should not modify the original object', () => {
      const testObj = {
        key1: 'value1',
        key2: 'value2',
        key3: 'value3',
      };
      const originalObj = { ...testObj };
      omitKeys({ obj: testObj, keysToRemove: ['key1'] });
      expect(testObj).toEqual(originalObj);
    });
  });

  describe('pickKeys', () => {
    it('should return an empty object when given an empty object', () => {
      const result = pickKeys({ obj: {}, keysToPick: ['key1', 'key2'] });
      expect(result).toEqual({});
    });

    it('should return an empty object when keysToPick is empty', () => {
      const testObj = { key1: 'value1', key2: 'value2' };
      const result = pickKeys({ obj: testObj, keysToPick: [] });
      expect(result).toEqual({});
    });

    it('should pick only specified keys from the object', () => {
      const testObj = {
        key1: 'value1',
        key2: 'value2',
        key3: 'value3',
        key4: 'value4',
      };
      const result = pickKeys({ obj: testObj, keysToPick: ['key1', 'key3'] });
      expect(result).toEqual({
        key1: 'value1',
        key3: 'value3',
      });
    });

    it('should handle case-insensitive key matching', () => {
      const testObj = {
        Key1: 'value1',
        KEY2: 'value2',
        key3: 'value3',
        kEy4: 'value4',
      };
      const result = pickKeys({ obj: testObj, keysToPick: ['key1', 'key3'] });
      expect(result).toEqual({
        Key1: 'value1',
        key3: 'value3',
      });
    });

    it('should handle keys that do not exist in the object', () => {
      const testObj = {
        key1: 'value1',
        key2: 'value2',
      };
      const result = pickKeys({ obj: testObj, keysToPick: ['key1', 'key3'] });
      expect(result).toEqual({
        key1: 'value1',
      });
    });

    it('should handle objects with non-string values', () => {
      const testObj = {
        key1: 123,
        key2: true,
        key3: { nestedKey: 'value' },
        key4: [1, 2, 3],
      };
      const result = pickKeys({ obj: testObj, keysToPick: ['key1', 'key3'] });
      expect(result).toEqual({
        key1: 123,
        key3: { nestedKey: 'value' },
      });
    });

    it('should not modify the original object', () => {
      const testObj = {
        key1: 'value1',
        key2: 'value2',
        key3: 'value3',
      };
      const originalObj = { ...testObj };
      pickKeys({ obj: testObj, keysToPick: ['key1'] });
      expect(testObj).toEqual(originalObj);
    });
  });

  describe('Combined usage', () => {
    it('should allow chaining omitKeys and pickKeys', () => {
      const testObj = {
        key1: 'value1',
        key2: 'value2',
        key3: 'value3',
        key4: 'value4',
        key5: 'value5',
      };

      // First omit key1 and key2, then pick key3 and key4
      const intermediate = omitKeys({
        obj: testObj,
        keysToRemove: ['key1', 'key2'],
      });
      const result = pickKeys({
        obj: intermediate,
        keysToPick: ['key3', 'key4'],
      });

      expect(result).toEqual({
        key3: 'value3',
        key4: 'value4',
      });
    });

    it('should produce the same result when using pickKeys first then omitKeys', () => {
      const testObj = {
        key1: 'value1',
        key2: 'value2',
        key3: 'value3',
        key4: 'value4',
        key5: 'value5',
      };

      // First pick key2, key3, key4, then omit key3
      const intermediate = pickKeys({
        obj: testObj,
        keysToPick: ['key2', 'key3', 'key4'],
      });
      const result = omitKeys({ obj: intermediate, keysToRemove: ['key3'] });

      expect(result).toEqual({
        key2: 'value2',
        key4: 'value4',
      });
    });
  });
});
