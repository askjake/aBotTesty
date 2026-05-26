import { calcTotalAttachments } from '@shared/ui/utils/attachments.utils';
import { FileType } from '@shared/ui/types/attachments.types';

describe('Attachments Utils', () => {
  describe('calcTotalAttachments', () => {
    // Mock file types for testing
    const mockImageTypes = {
      'image/jpeg': 'jpg',
      'image/png': 'png',
      'image/gif': 'gif',
    };

    const mockDocumentTypes = {
      'application/pdf': 'pdf',
      'text/plain': 'txt',
      'application/msword': 'doc',
    };

    // Helper function to create mock FileType objects
    const createMockFile = (name: string, type: string): FileType => ({
      uid: `${Math.random().toString(36).substring(2, 11)}`,
      name,
      fileName: name,
      type,
      size: 1024,
      lastModified: Date.now(),
      lastModifiedDate: new Date(),
      percent: 0,
      status: 'done',
    });

    it('should return 0 for empty attachments array', () => {
      const result = calcTotalAttachments({
        attachments: [],
        types: mockImageTypes,
      });

      expect(result).toBe(0);
    });

    it('should count only image files when image types are provided', () => {
      const attachments: FileType[] = [
        createMockFile('photo1.jpg', 'image/jpeg'),
        createMockFile('photo2.png', 'image/png'),
        createMockFile('document.pdf', 'application/pdf'),
        createMockFile('notes.txt', 'text/plain'),
      ];

      const result = calcTotalAttachments({
        attachments,
        types: mockImageTypes,
      });

      expect(result).toBe(2); // Only the 2 image files should be counted
    });

    it('should count only document files when document types are provided', () => {
      const attachments: FileType[] = [
        createMockFile('photo1.jpg', 'image/jpeg'),
        createMockFile('photo2.png', 'image/png'),
        createMockFile('document.pdf', 'application/pdf'),
        createMockFile('notes.txt', 'text/plain'),
      ];

      const result = calcTotalAttachments({
        attachments,
        types: mockDocumentTypes,
      });

      expect(result).toBe(2); // Only the 2 document files should be counted
    });

    it('should count all files when all types are provided', () => {
      const attachments: FileType[] = [
        createMockFile('photo1.jpg', 'image/jpeg'),
        createMockFile('photo2.png', 'image/png'),
        createMockFile('document.pdf', 'application/pdf'),
        createMockFile('notes.txt', 'text/plain'),
      ];

      const allTypes = {
        ...mockImageTypes,
        ...mockDocumentTypes,
      };

      const result = calcTotalAttachments({
        attachments,
        types: allTypes,
      });

      expect(result).toBe(4); // All files should be counted
    });

    it('should return 0 when no matching file types are found', () => {
      const attachments: FileType[] = [
        createMockFile('video.mp4', 'video/mp4'),
        createMockFile('audio.mp3', 'audio/mpeg'),
      ];

      const result = calcTotalAttachments({
        attachments,
        types: mockImageTypes,
      });

      expect(result).toBe(0); // No matching file types
    });

    it('should handle undefined type in attachments', () => {
      const attachments: FileType[] = [
        createMockFile('photo1.jpg', 'image/jpeg'),
        { ...createMockFile('unknown.file', ''), type: undefined } as FileType,
      ];

      const result = calcTotalAttachments({
        attachments,
        types: mockImageTypes,
      });

      expect(result).toBe(1); // Only the image file should be counted
    });

    it('should handle empty types object', () => {
      const attachments: FileType[] = [
        createMockFile('photo1.jpg', 'image/jpeg'),
        createMockFile('document.pdf', 'application/pdf'),
      ];

      const result = calcTotalAttachments({
        attachments,
        types: {},
      });

      expect(result).toBe(0); // No types to match against
    });
  });
});
