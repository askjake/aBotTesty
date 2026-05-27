import { SenderHeaderProps } from '@ant-design/x/es/sender/SenderHeader';

import {
  AttachmentStatusResponseType,
  AttachmentType,
  FileType,
} from '@shared/ui/types/attachments.types';
import { RefObject } from 'react';

export interface SenderHeaderBlockProps extends SenderHeaderProps {
  onAddAttachment: (
    value: FileType[],
  ) => Promise<{ attachments: AttachmentType[] }>;
  onRemoveAttachment: (value: string) => void;
  setLoading: (loading: boolean) => void;
  componentRef: RefObject<SenderHeaderBlockRef | null>;
}

export type SenderHeaderBlockRef = {
  resetAttachments: () => void;
};
