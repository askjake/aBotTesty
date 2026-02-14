import { AttachmentStatusEnum } from '@shared/ui/enums/chats.enums';
import { UploadFile } from 'antd';

export type AttachmentType = {
  attachment_id: string;
  filename: string;
  media_type: string;
  status: AttachmentStatusEnum;
  created_at: string;
  updated_at: string;
  vault_mode: boolean;
  owner_id: string;
  error_message?: string;
};

export type AttachmentStatusType = AttachmentType & {
  progress: number;
  message?: string;
  error_message?: string;
};

export type AttachmentStatusResponseType = {
  status: {
    [key: string]: AttachmentStatusType;
  };
};
export type FileType = UploadFile & {
  attachment_id?: string;
};

export type FileValidationErrorType = {
  type:
    | 'invalid_type'
    | 'invalid_size'
    | 'total_count'
    | 'image_count'
    | 'document_count';
  message: string;
  details?: {
    current: number;
    maximum: number;
    files: Array<{
      name: string;
      type: string;
    }>;
  };
};
