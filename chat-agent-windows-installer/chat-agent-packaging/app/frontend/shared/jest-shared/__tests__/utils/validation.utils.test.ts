import {
  isImageType,
  isDocumentType,
  categorizeFiles,
} from '@shared/ui/utils/validation.utils';

import {
  ALLOWED_DOCUMENTS_MIME_TYPES,
  ALLOWED_IMAGES_MIME_TYPES,
} from '@shared/ui/constants/validation.constants';

describe('File Utilities', () => {
  describe('isImageType', () => {
    it('should return true for allowed image MIME types', () => {
      // Test each allowed image MIME type from the constants
      Object.keys(ALLOWED_IMAGES_MIME_TYPES).forEach((mimeType) => {
        expect(isImageType(mimeType)).toBe(true);
      });
    });

    it('should return false for document MIME types', () => {
      // Test each document MIME type from the constants
      Object.keys(ALLOWED_DOCUMENTS_MIME_TYPES).forEach((mimeType) => {
        expect(isImageType(mimeType)).toBe(false);
      });
    });

    it('should return false for unknown MIME types', () => {
      expect(isImageType('image/tiff')).toBe(false);
      expect(isImageType('image/svg+xml')).toBe(false);
      expect(isImageType('unknown/type')).toBe(false);
      expect(isImageType('')).toBe(false);
    });
  });

  describe('isDocumentType', () => {
    it('should return true for allowed document MIME types', () => {
      // Test each allowed document MIME type from the constants
      Object.keys(ALLOWED_DOCUMENTS_MIME_TYPES).forEach((mimeType) => {
        expect(isDocumentType(mimeType)).toBe(true);
      });
    });

    it('should return false for image MIME types', () => {
      // Test each image MIME type from the constants
      Object.keys(ALLOWED_IMAGES_MIME_TYPES).forEach((mimeType) => {
        expect(isDocumentType(mimeType)).toBe(false);
      });
    });

    it('should return false for unknown MIME types', () => {
      expect(isDocumentType('application/zip')).toBe(false);
      expect(isDocumentType('application/json')).toBe(false);
      expect(isDocumentType('unknown/type')).toBe(false);
      expect(isDocumentType('')).toBe(false);
    });
  });

  describe('categorizeFiles', () => {
    // Helper function to create mock File objects
    function createMockFile(name: string, type: string): File {
      return {
        name,
        type,
        size: 1024,
        lastModified: Date.now(),
        slice: jest.fn(),
        arrayBuffer: jest.fn(),
        stream: jest.fn(),
        text: jest.fn(),
      } as unknown as File;
    }

    it('should correctly categorize image and document files', () => {
      // Create a mix of image and document files using the actual allowed MIME types
      const imageType = Object.keys(ALLOWED_IMAGES_MIME_TYPES)[0]; // e.g., 'image/jpeg'
      const documentType = Object.keys(ALLOWED_DOCUMENTS_MIME_TYPES)[0]; // e.g., 'text/plain'

      const files = [
        // @ts-ignore
        createMockFile('image1.jpg', imageType),
        // @ts-ignore
        createMockFile('document1.txt', documentType),
        // @ts-ignore
        createMockFile('image2.jpg', imageType),
        // @ts-ignore
        createMockFile('document2.txt', documentType),
      ];

      const result = categorizeFiles(files);

      expect(result.images).toHaveLength(2);
      expect(result.documents).toHaveLength(2);

      expect(result.images[0]?.type).toBe(imageType);
      expect(result.images[1]?.type).toBe(imageType);

      expect(result.documents[0]?.type).toBe(documentType);
      expect(result.documents[1]?.type).toBe(documentType);
    });

    it('should categorize all supported image types', () => {
      // Create a file for each supported image MIME type
      const files = Object.keys(ALLOWED_IMAGES_MIME_TYPES).map(
        (mimeType, index) => {
          const extension =
            ALLOWED_IMAGES_MIME_TYPES[
              mimeType as keyof typeof ALLOWED_IMAGES_MIME_TYPES
            ][0];
          return createMockFile(`image${index}${extension}`, mimeType);
        },
      );

      const result = categorizeFiles(files);

      expect(result.images).toHaveLength(
        Object.keys(ALLOWED_IMAGES_MIME_TYPES).length,
      );
      expect(result.documents).toHaveLength(0);

      // Verify each file was categorized correctly
      result.images.forEach((file) => {
        expect(Object.keys(ALLOWED_IMAGES_MIME_TYPES)).toContain(file.type);
      });
    });

    it('should categorize all supported document types', () => {
      // Create a file for each supported document MIME type
      const files = Object.keys(ALLOWED_DOCUMENTS_MIME_TYPES).map(
        (mimeType, index) => {
          const extension =
            ALLOWED_DOCUMENTS_MIME_TYPES[
              mimeType as keyof typeof ALLOWED_DOCUMENTS_MIME_TYPES
            ][0];
          return createMockFile(`document${index}${extension}`, mimeType);
        },
      );

      const result = categorizeFiles(files);

      expect(result.images).toHaveLength(0);
      expect(result.documents).toHaveLength(
        Object.keys(ALLOWED_DOCUMENTS_MIME_TYPES).length,
      );

      // Verify each file was categorized correctly
      result.documents.forEach((file) => {
        expect(Object.keys(ALLOWED_DOCUMENTS_MIME_TYPES)).toContain(file.type);
      });
    });

    it('should ignore unsupported file types', () => {
      const imageType = Object.keys(ALLOWED_IMAGES_MIME_TYPES)[0];
      const documentType = Object.keys(ALLOWED_DOCUMENTS_MIME_TYPES)[0];

      const files = [
        // @ts-ignore
        createMockFile('image.jpg', imageType),
        createMockFile('audio.mp3', 'audio/mpeg'),
        // @ts-ignore
        createMockFile('document.txt', documentType),
        createMockFile('archive.zip', 'application/zip'),
      ];

      const result = categorizeFiles(files);

      expect(result.images).toHaveLength(1);
      expect(result.documents).toHaveLength(1);
      expect(result.images[0]?.type).toBe(imageType);
      expect(result.documents[0]?.type).toBe(documentType);
    });

    it('should handle empty file array', () => {
      const result = categorizeFiles([]);

      expect(result.images).toHaveLength(0);
      expect(result.documents).toHaveLength(0);
    });

    it('should handle files with empty MIME types', () => {
      const files = [
        createMockFile('unknown1', ''),
        createMockFile('unknown2', ''),
      ];

      const result = categorizeFiles(files);

      expect(result.images).toHaveLength(0);
      expect(result.documents).toHaveLength(0);
    });
  });
});
