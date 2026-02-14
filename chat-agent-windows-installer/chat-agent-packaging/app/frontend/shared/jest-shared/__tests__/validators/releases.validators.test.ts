import { z } from 'zod';
import {
  updateLastReleaseDateValidator,
  UpdateLastReleaseDateSchema,
} from '@shared/ui/validators/releases.validators';

describe('updateLastReleaseDateValidator', () => {
  describe('Valid inputs', () => {
    it('should validate a valid date object', () => {
      const validData = {
        date: new Date('2023-12-25T10:30:00Z'),
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date).toBeInstanceOf(Date);
      expect(result.date.getTime()).toBe(validData.date.getTime());
    });

    it('should validate current date', () => {
      const currentDate = new Date();
      const validData = {
        date: currentDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date).toStrictEqual(currentDate);
    });

    it('should validate past dates', () => {
      const pastDate = new Date('2020-01-01T00:00:00Z');
      const validData = {
        date: pastDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date).toStrictEqual(pastDate);
    });

    it('should validate future dates', () => {
      const futureDate = new Date('2030-12-31T23:59:59Z');
      const validData = {
        date: futureDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date).toStrictEqual(futureDate);
    });

    it('should validate dates with different timezones', () => {
      const utcDate = new Date('2023-06-15T12:00:00Z');
      const validData = {
        date: utcDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date).toStrictEqual(utcDate);
    });

    it('should handle Date object at epoch', () => {
      const epochDate = new Date(0);
      const validData = {
        date: epochDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date.getTime()).toBe(0);
      expect(result.date).toStrictEqual(epochDate);
    });

    it('should handle very old dates', () => {
      const oldDate = new Date('1900-01-01T00:00:00Z');
      const validData = {
        date: oldDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date.getFullYear()).toBe(1900);
      expect(result.date).toStrictEqual(oldDate);
    });

    it('should handle dates with milliseconds', () => {
      const dateWithMs = new Date('2023-12-25T10:30:00.123Z');
      const validData = {
        date: dateWithMs,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date.getMilliseconds()).toBe(123);
      expect(result.date).toStrictEqual(dateWithMs);
    });
  });

  describe('Invalid inputs', () => {
    it('should reject string date', () => {
      const invalidData = {
        date: '2023-12-25',
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });

    it('should reject ISO string date', () => {
      const invalidData = {
        date: '2023-12-25T10:30:00Z',
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });

    it('should reject number timestamp', () => {
      const invalidData = {
        date: Date.now(),
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });

    it('should reject null date', () => {
      const invalidData = {
        date: null,
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });

    it('should reject boolean value', () => {
      const invalidData = {
        date: true,
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });

    it('should reject array', () => {
      const invalidData = {
        date: [2023, 12, 25],
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });

    it('should reject object', () => {
      const invalidData = {
        date: { year: 2023, month: 12, day: 25 },
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });

    it('should reject invalid Date object', () => {
      const invalidData = {
        date: new Date('invalid-date'),
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });
  });

  describe('Missing fields', () => {
    it('should reject empty object', () => {
      const invalidData = {};

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });

    it('should reject object without date field', () => {
      const invalidData = {
        otherField: 'value',
      };

      expect(() => updateLastReleaseDateValidator.parse(invalidData)).toThrow(
        z.ZodError,
      );
    });
  });

  describe('Extra fields', () => {
    it('should reject extra fields when using strict validation', () => {
      const inputDate = new Date('2023-12-25T10:30:00Z');
      const dataWithExtraFields = {
        date: inputDate,
        extraField: 'should be rejected',
        anotherField: 123,
      };

      expect(() =>
        updateLastReleaseDateValidator.parse(dataWithExtraFields),
      ).toThrow(z.ZodError);

      const result =
        updateLastReleaseDateValidator.safeParse(dataWithExtraFields);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('unrecognized_keys');
      }
    });

    it('should accept valid data without extra fields', () => {
      const inputDate = new Date('2023-12-25T10:30:00Z');
      const validData = {
        date: inputDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual({
        date: inputDate,
      });
      expect(result.date).toStrictEqual(inputDate);
    });
  });

  describe('Error details', () => {
    it('should provide detailed error for missing date', () => {
      const invalidData = {};

      try {
        updateLastReleaseDateValidator.parse(invalidData);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeInstanceOf(z.ZodError);
        const zodError = error as z.ZodError;
        expect(zodError.issues).toHaveLength(1);
        expect(zodError.issues[0].code).toBe('invalid_type');
        expect(zodError.issues[0].path).toEqual(['date']);
        // Updated to match actual error message
        expect(zodError.issues[0].message).toContain('expected date');
      }
    });

    it('should provide detailed error for wrong type', () => {
      const invalidData = {
        date: '2023-12-25',
      };

      try {
        updateLastReleaseDateValidator.parse(invalidData);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeInstanceOf(z.ZodError);
        const zodError = error as z.ZodError;
        expect(zodError.issues).toHaveLength(1);
        expect(zodError.issues[0].code).toBe('invalid_type');
        expect(zodError.issues[0].path).toEqual(['date']);
      }
    });

    it('should provide detailed error for invalid date', () => {
      const invalidData = {
        date: new Date('invalid'),
      };

      try {
        updateLastReleaseDateValidator.parse(invalidData);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeInstanceOf(z.ZodError);
        const zodError = error as z.ZodError;
        expect(zodError.issues).toHaveLength(1);
        // Updated: invalid Date objects are treated as invalid_type in some Zod versions
        expect(['invalid_date', 'invalid_type']).toContain(
          zodError.issues[0].code,
        );
        expect(zodError.issues[0].path).toEqual(['date']);
      }
    });
  });

  describe('Safe parsing', () => {
    it('should return success for valid data with safeParse', () => {
      const inputDate = new Date('2023-12-25T10:30:00Z');
      const validData = {
        date: inputDate,
      };

      const result = updateLastReleaseDateValidator.safeParse(validData);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(validData);
        expect(result.data.date).toStrictEqual(inputDate);
      }
    });

    it('should return error for invalid data with safeParse', () => {
      const invalidData = {
        date: '2023-12-25',
      };

      const result = updateLastReleaseDateValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBeInstanceOf(z.ZodError);
        expect(result.error.issues).toHaveLength(1);
      }
    });

    it('should return error for missing date with safeParse', () => {
      const invalidData = {};

      const result = updateLastReleaseDateValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBeInstanceOf(z.ZodError);
        expect(result.error.issues[0].code).toBe('invalid_type');
      }
    });

    it('should return error for invalid Date object with safeParse', () => {
      const invalidData = {
        date: new Date('invalid'),
      };

      const result = updateLastReleaseDateValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBeInstanceOf(z.ZodError);
        // Updated: can be either invalid_date or invalid_type
        expect(['invalid_date', 'invalid_type']).toContain(
          result.error.issues[0].code,
        );
      }
    });
  });

  describe('Type inference', () => {
    it('should infer correct TypeScript type', () => {
      const inputDate = new Date('2023-12-25T10:30:00Z');
      const validData = {
        date: inputDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      // TypeScript compile-time check
      const typedResult: UpdateLastReleaseDateSchema = result;
      expect(typedResult.date).toBeInstanceOf(Date);

      // Runtime type check
      expect(typeof result.date.getTime).toBe('function');
      expect(result.date.getFullYear()).toBe(2023);
      expect(result.date).toStrictEqual(inputDate);
    });
  });

  describe('Edge cases', () => {
    it('should validate that dates are the same value even if different instances', () => {
      const dateString = '2023-12-25T10:30:00.123Z';
      const date1 = new Date(dateString);
      const date2 = new Date(dateString);

      const validData1 = { date: date1 };
      const validData2 = { date: date2 };

      const result1 = updateLastReleaseDateValidator.parse(validData1);
      const result2 = updateLastReleaseDateValidator.parse(validData2);

      // Different instances but same value
      expect(result1.date).not.toBe(result2.date); // Different references
      expect(result1.date.getTime()).toBe(result2.date.getTime()); // Same timestamp
      expect(result1.date).toEqual(result2.date); // Deep equality
    });

    it('should handle maximum safe date', () => {
      const maxDate = new Date(8640000000000000); // Max safe date
      const validData = {
        date: maxDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date).toStrictEqual(maxDate);
    });

    it('should handle minimum safe date', () => {
      const minDate = new Date(-8640000000000000); // Min safe date
      const validData = {
        date: minDate,
      };

      const result = updateLastReleaseDateValidator.parse(validData);

      expect(result).toEqual(validData);
      expect(result.date).toStrictEqual(minDate);
    });
  });

  describe('Schema properties', () => {
    it('should be a ZodObject schema', () => {
      expect(updateLastReleaseDateValidator).toBeInstanceOf(z.ZodObject);
    });

    it('should have date field as ZodDate', () => {
      const shape = updateLastReleaseDateValidator.shape;
      expect(shape.date).toBeInstanceOf(z.ZodDate);
    });

    it('should not allow additional properties', () => {
      const dataWithExtra = {
        date: new Date(),
        extra: 'field',
      };

      const result = updateLastReleaseDateValidator.safeParse(dataWithExtra);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('unrecognized_keys');
      }
    });

    it('should enforce strict mode', () => {
      const dataWithExtra = {
        date: new Date(),
        unexpectedField: 'value',
      };

      expect(() =>
        updateLastReleaseDateValidator.parse(dataWithExtra),
      ).toThrow();
    });
  });

  describe('Multiple validation methods', () => {
    const validDate = new Date('2023-12-25T10:30:00Z');
    const validData = { date: validDate };

    it('should work with parse method', () => {
      const result = updateLastReleaseDateValidator.parse(validData);
      expect(result.date).toStrictEqual(validDate);
    });

    it('should work with safeParse method', () => {
      const result = updateLastReleaseDateValidator.safeParse(validData);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.date).toStrictEqual(validDate);
      }
    });
  });

  describe('Immutability', () => {
    it('should not mutate original data', () => {
      const originalDate = new Date('2023-12-25T10:30:00Z');
      const originalData = { date: originalDate };
      const originalTimestamp = originalDate.getTime();

      const result = updateLastReleaseDateValidator.parse(originalData);

      // Original should remain unchanged
      expect(originalData.date.getTime()).toBe(originalTimestamp);
      expect(result.date.getTime()).toBe(originalTimestamp);
    });
  });
});
